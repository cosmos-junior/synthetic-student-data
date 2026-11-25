"""Generate synthetic student data using CTGAN."""

from sdv.single_table import CTGANSynthesizer

from src.synthetic_data.generation_utils import run_synthesizer_pipeline


def generate_ctgan(
    number_of_rows=500,
    epochs=300,
    batch_size=500,
    verbose=True,
):
    """Train and sample from a CTGAN synthesizer."""

    return run_synthesizer_pipeline(
        synthesizer_factory=lambda metadata: CTGANSynthesizer(
            metadata,
            enforce_min_max_values=True,
            enforce_rounding=True,
            epochs=epochs,
            batch_size=batch_size,
            verbose=verbose,
        ),
        model_name="CTGAN",
        output_filename="ctgan_synthetic.csv",
        number_of_rows=number_of_rows,
    )


if __name__ == "__main__":
    generate_ctgan()
