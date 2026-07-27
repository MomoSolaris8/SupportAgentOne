from supportagent.evaluation.schemas import EvaluationMetric


def rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def minimum_metric(name: str, value: float, threshold: float) -> EvaluationMetric:
    return EvaluationMetric(
        name=name,
        value=value,
        threshold=threshold,
        comparator="gte",
        passed=value >= threshold,
    )


def maximum_metric(name: str, value: float, threshold: float) -> EvaluationMetric:
    return EvaluationMetric(
        name=name,
        value=value,
        threshold=threshold,
        comparator="lte",
        passed=value <= threshold,
    )
