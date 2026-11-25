"""Generate synthetic student data using Gaussian Copula."""

from sdv.single_table import GaussianCopulaSynthesizer

from src.synthetic_data.generation_utils import run_synthesizer_pipeline


def generate_gaussian_copula(number_of_rows=500):
    """Train and sample from a Gaussian Copula synthesizer."""

    return run_synthesizer_pipeline(
        synthesizer_factory=lambda metadata: GaussianCopulaSynthesizer(
            metadata,
            enforce_min_max_values=True,
            enforce_rounding=True,
        ),
        model_name="Gaussian Copula",
        output_filename="gaussian_copula_synthetic.csv",
        number_of_rows=number_of_rows,
    )


if __name__ == "__main__":
    generate_gaussian_copula()
