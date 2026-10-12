from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass
class Campaign:
    id: str
    name: str
    url: str
    cpm_usd: float
    budget_left_usd: Optional[float]
    platforms: list
    rules_text: str
    source_links: list = field(default_factory=list)
    requires_editing: Optional[bool] = None
    min_payout_usd: Optional[float] = None
    max_payout_usd: Optional[float] = None
    budget_used_usd: Optional[float] = None
    budget_total_usd: Optional[float] = None
    eligible_for_new_youtube_shorts_channels: object = None
    requires_draft_preapproval: bool = False
    owner_requirements: list = field(default_factory=list)


@dataclass
class Clip:
    id: str
    campaign_id: str
    source_id: str
    start_s: float
    end_s: float
    path: str
    title: str
    description: str
    hashtags: list
    channel_handle: str
    caption_words: list = field(default_factory=list)
    passthrough: bool = False
    source_route: str = ""
    render_seconds: float = 0.0


@dataclass
class Post:
    clip_id: str
    channel_handle: str
    platform: str
    video_id: str
    url: str
    posted_at: str


class Uploader(Protocol):
    def upload(self, clip: Clip, *, dry_run: bool = False) -> Post: ...


class Submitter(Protocol):
    def submit(self, campaign: Campaign, post: Post, *, dry_run: bool = False) -> str: ...


class Scout(Protocol):
    def list_campaigns(self) -> list[Campaign]: ...
