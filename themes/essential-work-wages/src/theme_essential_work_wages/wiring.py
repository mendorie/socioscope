from socioscope_core.core.pipeline import Pipeline, Stage
from theme_essential_work_wages import pipeline

PIPELINE = Pipeline(
    slug="essential-work-wages",
    title="エッセンシャルワークの逆説（社会に不可欠な仕事ほどなぜ低賃金か）",
)
PIPELINE.register(Stage.FETCH)(pipeline.fetch)
PIPELINE.register(Stage.STAGE)(pipeline.stage)
PIPELINE.register(Stage.MART)(pipeline.mart)
