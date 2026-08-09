## ADDED Requirements

### Requirement: Derive missing frame hashes from the frame image on disk
When loading a feedback entry whose JSON records no `frame_hashes` (an entry written before frame-hash tracking existed, or one whose list is empty), the system SHALL derive its frame hashes from the full-resolution frame image referenced by `frame_path`, when that file still exists on disk. The derived hashes SHALL use the same scheme as the live capture path — the SHA-256 hex digest of the decoded image's raw bytes — so a derived hash and a live hash of the same image are equal. Derivation SHALL happen in memory at load time; the system SHALL NOT rewrite the entry's JSON on disk.

When an entry has no recorded hashes and no resolvable `frame_path`, or the frame image cannot be decoded, its frame hashes SHALL be treated as unknown — never as a fingerprint that can match a current frame set (see `feedback-deduplication`) — and the entry SHALL load successfully with all its other content intact.

#### Scenario: Entry with no recorded hashes but a resolvable frame
- **WHEN** an entry JSON has no `frame_hashes` and its `frame_path` references a frame file that still exists
- **THEN** the entry loads with frame hashes derived from that image, equal to the hash the live capture path would produce for the same image

#### Scenario: Derived hashes are not written back
- **WHEN** an entry's frame hashes have been derived from disk
- **THEN** the entry's JSON file on disk is left byte-for-byte unchanged

#### Scenario: Entry with no recorded hashes and no frame on disk
- **WHEN** an entry JSON has no `frame_hashes` and either no `frame_path` or one whose file no longer exists
- **THEN** the entry loads with its frame hashes treated as unknown, and its text, mode, timestamp, and observations are unaffected

#### Scenario: Undecodable frame image
- **WHEN** an entry has no recorded hashes and its `frame_path` references a file that cannot be decoded as an image
- **THEN** the failure is logged, the entry loads with its frame hashes treated as unknown, and loading of the remaining entries continues

#### Scenario: Recorded hashes are left alone
- **WHEN** an entry JSON already records a non-empty `frame_hashes` list
- **THEN** those hashes are used as-is and no frame image is decoded for it
