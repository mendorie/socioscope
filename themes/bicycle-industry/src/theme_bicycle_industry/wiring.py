from socioscope_core.core.pipeline import Pipeline, Stage
from theme_bicycle_industry import pipeline

PIPELINE = Pipeline(
    slug="bicycle-industry", title="自転車産業の現状（日本・世界、自動車・二輪との対比）"
)
PIPELINE.register(Stage.FETCH)(pipeline.fetch)
PIPELINE.register(Stage.STAGE)(pipeline.stage)
PIPELINE.register(Stage.MART)(pipeline.mart)
