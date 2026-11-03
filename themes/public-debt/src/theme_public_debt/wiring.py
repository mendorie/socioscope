from socioscope_core.core.pipeline import Pipeline, Stage
from theme_public_debt import pipeline

PIPELINE = Pipeline(
    slug="public-debt",
    title="資本主義国家の負債は過去からどう推移してきたか（「資本主義の終焉」はどれだけ近いか）",
)
PIPELINE.register(Stage.FETCH)(pipeline.fetch)
PIPELINE.register(Stage.STAGE)(pipeline.stage)
PIPELINE.register(Stage.MART)(pipeline.mart)
