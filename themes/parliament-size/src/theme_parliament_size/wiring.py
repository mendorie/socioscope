from socioscope_core.core.pipeline import Pipeline, Stage
from theme_parliament_size import pipeline

PIPELINE = Pipeline(
    slug="parliament-size",
    title="国会議員定数の削減は適切か（人口比・役割の範囲・比例代表・一票の格差・国費）",
)
PIPELINE.register(Stage.FETCH)(pipeline.fetch)
PIPELINE.register(Stage.STAGE)(pipeline.stage)
PIPELINE.register(Stage.MART)(pipeline.mart)
