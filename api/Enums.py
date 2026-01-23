from enum import Enum
class DocumentScope(str, Enum):
    law = "법령"
    rule = "규칙"
    sheet = "공고문"
