from wenyan_models.status.chapter import ChapterStatus
from wenyan_models.status.document import DocumentStatus
from wenyan_models.status.paragraph import ParagraphStatus
from wenyan_models.status.segment import SegmentStatus

StatusPayload = DocumentStatus | ChapterStatus | ParagraphStatus | SegmentStatus
