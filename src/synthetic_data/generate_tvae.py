"""Generate synthetic student data using TVAE."""

from sdv.single_table import TVAESynthesizer

from src.synthetic_data.generation_utils import run_synthesizer_pipeline


def generate_tvae(
    number_of_rows=500,
    epochs=300,
    batch_size=500,
    verbose=True,
):
    """Train and sample from a TVAE synthesizer."""

    return run_synthesizer_pipeline(
        synthesizer_factory=lambda metadata: TVAESynthesizer(
            metadata,
            enforce_min_max_values=True,
            enforce_rounding=True,
            epochs=epochs,
            batch_size=batch_size,
            verbose=verbose,
        ),
        model_name="TVAE",
        output_filename="tvae_synthetic.csv",
        number_of_rows=number_of_rows,
    )


if __name__ == "__main__":
    generate_tvae()
