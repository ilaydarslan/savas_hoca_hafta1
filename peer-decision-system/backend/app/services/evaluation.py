"""Measured classroom illustration, not an independent held-out benchmark."""
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter_ns

from app.services.scope_analysis import SCOPES, ConstantScopeStrategy, KeywordScopeStrategy

LABELS = [*SCOPES, 'REVIEW']
DATA_PATH = Path(__file__).resolve().parents[1] / 'data' / 'scope_benchmark.json'


def classification_metrics(expected: list[str], predicted: list[str | None]) -> dict:
    if len(expected) != len(predicted):
        raise ValueError('Expected and predicted lengths must match')
    matrix = [[0 for _ in LABELS] for _ in LABELS]
    for actual, prediction in zip(expected, predicted):
        matrix[LABELS.index(actual)][LABELS.index(prediction or 'REVIEW')] += 1
    per_class = []
    for index, label in enumerate(SCOPES):
        tp = matrix[index][index]
        support = sum(matrix[index])
        predicted_count = sum(row[index] for row in matrix)
        precision = tp / predicted_count if predicted_count else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class.append(dict(label=label, precision=precision, recall=recall, f1=f1, support=support))
    return {'accuracy': sum(matrix[i][i] for i in range(len(SCOPES))) / len(expected) if expected else 0.0,
            'macro_f1': sum(row['f1'] for row in per_class) / len(SCOPES),
            'coverage': sum(p is not None and p != 'REVIEW' for p in predicted) / len(predicted) if predicted else 0.0,
            'per_class': per_class, 'confusion_matrix': matrix}


def evaluate() -> dict:
    raw = DATA_PATH.read_bytes()
    dataset = json.loads(raw)
    samples = dataset['samples']
    methods = []
    for method_id, name, strategy in (
        ('constant', 'Sabit COMMUNITY referansı', ConstantScopeStrategy()),
        ('keyword', 'Türkçe anahtar sözcük stratejisi', KeywordScopeStrategy()),
    ):
        predictions, latencies = [], []
        for sample in samples:
            start = perf_counter_ns()
            predicted = strategy.predict(sample['text'])
            latencies.append((perf_counter_ns() - start) / 1_000_000)
            predictions.append({**sample, 'predicted': predicted or 'REVIEW'})
        metrics = classification_metrics([s['expected'] for s in samples], [s['predicted'] for s in predictions])
        methods.append({'id': method_id, 'name': name, **metrics,
                        'latency_p95_ms': sorted(latencies)[math.ceil(.95 * len(latencies)) - 1],
                        'errors': [s for s in predictions if s['expected'] != s['predicted']],
                        'predictions': predictions})
    return {'dataset': {'version': dataset['version'], 'source': dataset['source'],
                         'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(samples),
                         'limitations': dataset['limitations']},
            'labels': LABELS,
            'distribution': [{'label': label, 'count': sum(s['expected'] == label for s in samples)} for label in SCOPES],
            'methods': methods}
