from enum import Enum

class VectorDBProviderEnum(Enum):
    QDRANT = "QDRANT"
    

class DistanceMethodEnum(str, Enum):
    """
    Distance function types used to compare vectors
    """

    def __str__(self) -> str:
        return str(self.value)

    COSINE = "cosine"
    EUCLID = "euclid"
    DOT = "dot"
    # Manhattan distance is better to use with sparse vectors
    MANHATTAN = "manhattan"