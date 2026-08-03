# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from dataclasses import dataclass


@dataclass
class Media:
    id: str
    duration: str = "00:00"
    duration_sec: int = 0
    file_path: str | None = None
    stream_url: str | None = None
    message_id: int = 0
    title: str | None = None
    url: str | None = None
    time: int = 0
    user: str | None = None
    video: bool = False
    # Chat id the track originated from (set at play time) so background /
    # error logging knows where to report a playback failure.
    _chat_id: int = 0


@dataclass
class Track:
    id: str
    channel_name: str | None = None
    duration: str = "00:00"
    duration_sec: int = 0
    title: str | None = None
    url: str | None = None
    file_path: str | None = None
    stream_url: str | None = None
    message_id: int = 0
    time: int = 0
    thumbnail: str | None = None
    user: str | None = None
    view_count: str | None = None
    video: bool = False
    # Chat id the track originated from (set at play time) so background /
    # error logging knows where to report a playback failure.
    _chat_id: int = 0
