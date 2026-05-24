# Poll Post Database Design

Poll posts reuse the existing `post` table as the parent content record. A poll is a normal post with two to four related `poll_option` rows. Votes are stored separately in `poll_vote` so vote history can enforce one vote per user per poll.

## Tables

### `post`

Existing table used for all post types.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `Integer` | Primary key. |
| `body` | `Text` | Poll question text. Required for poll posts. |
| `media_filename` | `String(255)` | Must be `NULL` for poll posts. |
| `media_type` | `String(20)` | Must be `NULL` for poll posts. |
| `created_at` | `DateTime(timezone=True)` | Creation timestamp, indexed. |
| `author_id` | `Integer` | Foreign key to `user.id`. |
| `repost_of_id` | `Integer` | Optional self-reference for reposts. |

Relationship: one `post` has zero to four `poll_option` rows.

### `poll_option`

Stores the selectable choices for a poll post.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `Integer` | Primary key. |
| `text` | `String(160)` | Option label. Must be non-empty. |
| `position` | `Integer` | Display order from 1 to 4. |
| `post_id` | `Integer` | Foreign key to `post.id`, indexed. |

Constraints:

- `uq_poll_option_position`: each post can use a given option position once.
- `ck_poll_option_text`: option text must not be empty.
- `ck_poll_option_position_range`: position must be between 1 and 4.

Relationship: one `poll_option` has many `poll_vote` rows.

### `poll_vote`

Stores one user's vote in one poll.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `Integer` | Primary key. |
| `created_at` | `DateTime(timezone=True)` | Vote timestamp. |
| `post_id` | `Integer` | Foreign key to `post.id`, indexed. |
| `option_id` | `Integer` | Foreign key to `poll_option.id`, indexed. |
| `voter_id` | `Integer` | Foreign key to `user.id`, indexed. |

Constraints:

- `uq_poll_vote_once_per_post`: each user can vote only once per poll post.

## Result Calculation

`Post.total_poll_votes` sums vote counts across all options. `PollOption.percentage()` returns a rounded integer percentage for display. If a poll has no votes, every option displays `0%`.
