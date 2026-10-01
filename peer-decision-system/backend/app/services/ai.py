from typing import Protocol

class AnalysisProvider(Protocol):
    def analyze(self, topic, similar: list, rules: list) -> dict: ...

class MockAnalysisProvider:
    def analyze(self, topic, similar, rules):
        return {
            'provider': 'Mock AI · kural tabanlı demo',
            'summary': f'{topic.title}: {topic.description[:350]}',
            'argumentsFor': ['Ortak ihtiyaçların katılımcı biçimde ele alınmasını sağlar.', f'{topic.category} alanında birlikte öğrenme fırsatı oluşturabilir.'],
            'argumentsAgainst': ['Uygulama süresi ve kaynak ihtiyacı ayrıca değerlendirilmelidir.', 'Etkilenen takımın çekinceleri tartışmada açıklığa kavuşturulmalıdır.'],
            'possibleRuleConflicts': [r.description for r in rules if topic.impact_level == 'HIGH' or r.condition['kind'] in ('MINORITY_SUPPORT','QUORUM')],
            'similarTopics': [{'id': t.id, 'title': t.title} for t in similar],
            'notice': 'Bu çıktı örnek yardımcı analizdir; yapay zekâ karar vermez ve uzman görüşünün yerini almaz.'
        }

analysis_provider: AnalysisProvider = MockAnalysisProvider()
