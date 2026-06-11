# metrics package
from .basic_stats import compute as compute_basic_stats
from .lexical_diversity import compute as compute_lexical_diversity
from .readability import compute as compute_readability
from .structure import compute as compute_structure
from .tfidf_analysis import compute as compute_tfidf
from .water_content import compute as compute_water_content

METRIC_FUNCTIONS = {
    "basic_stats":       compute_basic_stats,
    "lexical_diversity": compute_lexical_diversity,
    "readability":       compute_readability,
    "structure":         compute_structure,
    "tfidf":             compute_tfidf,
    "water_content":     compute_water_content,
}
