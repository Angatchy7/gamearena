# GameArena REST API Documentation

GameArena provides a modular REST API layer built with Django REST Framework (DRF) running alongside the standard Django web application.

Base URL: `/api/`

---

## Authentication & Authorization

- **Authentication Method**: Session Authentication (`SessionAuthentication`).
- **Anonymous Endpoints**: Public read-only endpoints (Games, Tournaments, Members, Leaderboard, Matches, Statistics) are accessible anonymously (`AllowAny`).
- **Protected Endpoints**: Actions such as registration, user profile, dashboard summary, notifications, searching candidates for team invitations, and submitting match results require authentication (`IsAuthenticated`) and appropriate role-based permissions (Team Manager / Tournament Organizer).
- **Unauthenticated Response Behavior**: Unauthenticated requests to protected endpoints return HTTP `403 Forbidden` (Permission Denied).

---

## API Endpoints Summary

### 1. Games API

#### `GET /api/games/`
Returns a collection of active games with their total tournament counts.
- **Auth Required**: No
- **Response**: `200 OK`
```json
[
  {
    "id": 1,
    "name": "PUBG Mobile",
    "slug": "pubg-mobile",
    "image_url": "/static/images/games/pubg.svg",
    "tournament_count": 5
  }
]
```

#### `GET /api/games/{slug}/`
Returns detail for a single game.
- **Auth Required**: No
- **Response**: `200 OK` or `404 Not Found`
```json
{
  "id": 1,
  "name": "PUBG Mobile",
  "slug": "pubg-mobile",
  "description": "Battle Royale Game",
  "image_url": "/static/images/games/pubg.svg",
  "tournament_count": 5,
  "is_active": true,
  "created_at": "2026-08-15T12:00:00Z"
}
```

#### `GET /api/games/{slug}/tournaments/`
Returns tournaments associated with a specific game.
- **Auth Required**: No
- **Query Parameters**:
  - `status`: `registration_open`, `registration_closed`, `live`, `upcoming`, `completed`
  - `q`: Partial text search query
- **Response**: `200 OK`

---

### 2. Tournaments API

#### `GET /api/tournaments/`
Returns list of tournaments matching optional filters.
- **Auth Required**: No
- **Query Parameters**:
  - `game`: Game slug (e.g. `pubg-mobile`)
  - `status`: `registration_open`, `live`, `upcoming`, `completed`
  - `q`: Search query matching tournament name or description
- **Response**: `200 OK`
```json
[
  {
    "id": 10,
    "name": "PUBG Global Championship",
    "slug": "pubg-global-championship",
    "game": {
      "id": 1,
      "name": "PUBG Mobile",
      "slug": "pubg-mobile",
      "image_url": "/static/images/games/pubg.svg"
    },
    "organizer": "organizer_user",
    "status": "REGISTRATION_OPEN",
    "registration_status": "REGISTRATION_OPEN",
    "registration_start": "2026-08-15T00:00:00Z",
    "registration_end": "2026-08-18T00:00:00Z",
    "start_date": "2026-08-20T00:00:00Z",
    "end_date": "2026-08-25T00:00:00Z",
    "registration_fee": "0.00",
    "prize_pool": "1000.00",
    "cover_url": "/static/images/games/pubg.svg",
    "banner_url": "/static/images/games/pubg.svg",
    "participation_type": "TEAM",
    "team_size": 5,
    "max_participants": 16,
    "participant_count": 8
  }
]
```

#### `GET /api/tournaments/{id}/`
Returns detailed tournament information.
- **Auth Required**: No
- **Response**: `200 OK` or `404 Not Found`

---

### 3. Teams & Autocomplete API

#### `GET /api/teams/{slug}/members/`
Returns active team members for team `{slug}`.
- **Auth Required**: No
- **Response**: `200 OK`
```json
[
  {
    "id": 5,
    "username": "player_one",
    "team_role": "PLAYER",
    "joined_at": "2026-08-15T12:00:00Z"
  }
]
```

#### `GET /api/teams/{slug}/invite/search/?q={username}`
Asynchronously searches candidate players to invite to team `{slug}`.
- **Auth Required**: Yes (`IsAuthenticated`)
- **Permission**: Must be the Manager of team `{slug}` (`IsTeamManager`)
- **Behavior**: Case-insensitive search excluding manager, active members, and pending invitees. Limited to 10 results.
- **Response**: `200 OK` or `403 Forbidden`
```json
[
  {
    "id": 12,
    "username": "aadar"
  }
]
```

---

### 4. Tournament Registration API

#### `POST /api/tournaments/{id}/register/`
Registers the logged-in user (or their team) for tournament `{id}`.
- **Auth Required**: Yes (`IsAuthenticated`)
- **Requester Identity**: Derived automatically from `request.user`.
- **Response**:
  - `201 Created` on successful registration
  - `400 Bad Request` if registration is closed, full, duplicate, or player overlap exists
  - `401 Unauthorized` if unauthenticated
```json
{
  "id": 42,
  "tournament": 10,
  "tournament_name": "PUBG Global Championship",
  "display_name": "player_one",
  "status": "REGISTERED",
  "registered_at": "2026-08-15T14:00:00Z"
}
```

---

### 5. Leaderboard & Statistics API

#### `GET /api/tournaments/{id}/leaderboard/`
Returns leaderboard rankings and tournament completion statistics.
- **Auth Required**: No
- **Behavior**: Uses central display helpers. Returns real player usernames for SOLO tournaments (never exposes internal `__SOLO_` identifiers) and team names for TEAM tournaments.
- **Response**: `200 OK`
```json
{
  "tournament_id": 10,
  "tournament_name": "PUBG Global Championship",
  "total_matches": 7,
  "completed_matches": 7,
  "completion_percentage": 100,
  "total_goals": 21,
  "avg_goals": 3.0,
  "rankings": [
    {
      "rank": 1,
      "name": "Alpha Squad",
      "wins": 3,
      "losses": 0,
      "points": 9,
      "goals_scored": 10,
      "goals_conceded": 2,
      "goal_difference": 8
    }
  ]
}
```

---

### 6. Matches & Results API

#### `GET /api/tournaments/{id}/matches/`
Returns all rounds and matches for tournament `{id}`.
- **Auth Required**: No
- **Response**: `200 OK`

#### `GET /api/matches/{id}/`
Returns a single match detail.
- **Auth Required**: No
- **Response**: `200 OK`

#### `POST /api/matches/{id}/result/`
Updates match score and advances the winning team in the bracket.
- **Auth Required**: Yes (`IsAuthenticated` + `IsTournamentOrganizer`)
- **Body Parameters**:
```json
{
  "team_one_score": 2,
  "team_two_score": 1
}
```
- **Response**: `200 OK` on success, `403 Forbidden` if not tournament organizer, `400 Bad Request` if tie score submitted.

---

### 7. Notifications API

#### `GET /api/notifications/`
Returns notifications belonging to the logged-in user.
- **Auth Required**: Yes (`IsAuthenticated`)
- **Response**: `200 OK` or `401 Unauthorized`
```json
[
  {
    "id": 1,
    "title": "Team Invitation",
    "message": "You were invited to join Alpha Squad",
    "notification_type": "TEAM_INVITATION",
    "is_read": false,
    "created_at": "2026-08-15T12:00:00Z"
  }
]
```

#### `GET /api/notifications/unread/`
Returns unread count and unread notification items for the logged-in user.
- **Auth Required**: Yes (`IsAuthenticated`)
- **Response**: `200 OK`
```json
{
  "unread_count": 1,
  "results": [
    {
      "id": 1,
      "title": "Team Invitation",
      "message": "You were invited to join Alpha Squad",
      "notification_type": "TEAM_INVITATION",
      "is_read": false,
      "created_at": "2026-08-15T12:00:00Z"
    }
  ]
}
```

#### `POST /api/notifications/{id}/read/`
Marks a single notification as read. Prevents cross-user notification access.
- **Auth Required**: Yes (`IsAuthenticated`)
- **Response**: `200 OK` or `404 Not Found` if notification does not belong to user.

#### `POST /api/notifications/read-all/`
Marks all unread notifications for the logged-in user as read.
- **Auth Required**: Yes (`IsAuthenticated`)
- **Response**: `200 OK`
```json
{
  "updated_count": 3,
  "detail": "All notifications marked as read."
}
```

---

### 8. User Profile API

#### `GET /api/profile/`
Returns safe account details for the authenticated user. Strictly excludes password, tokens, credentials, or admin fields.
- **Auth Required**: Yes (`IsAuthenticated`)
- **Response**: `200 OK` or `401 Unauthorized`
```json
{
  "id": 12,
  "username": "aadar",
  "email": "aadar@example.com",
  "role": "USER"
}
```

---

### 9. Dashboard API

#### `GET /api/dashboard/`
Returns dashboard metrics, managed/joined teams summary, and recent activity for the logged-in user.
- **Auth Required**: Yes (`IsAuthenticated`)
- **Response**: `200 OK`
```json
{
  "user": {
    "id": 12,
    "username": "aadar",
    "role": "USER"
  },
  "metrics": {
    "managed_teams_count": 1,
    "joined_teams_count": 2,
    "organized_tournaments_count": 3,
    "active_organized_count": 1,
    "joined_tournaments_count": 4,
    "unread_notifications_count": 0
  },
  "teams": [
    {
      "id": 5,
      "name": "Alpha Squad",
      "slug": "alpha-squad",
      "logo_url": "/static/images/teams/default.png",
      "role": "MANAGER"
    }
  ],
  "recent_notifications": []
}
```

---

### 10. Tournament Statistics API

#### `GET /api/tournaments/{id}/statistics/`
Returns completion metrics, goal averages, and rankings. Automatically formats SOLO tournaments with real usernames and TEAM tournaments with team names (zero `__SOLO_` leakage).
- **Auth Required**: No
- **Response**: `200 OK`
```json
{
  "tournament_id": 10,
  "tournament_name": "PUBG Global Championship",
  "participation_type": "TEAM",
  "participant_count": 8,
  "registration_percentage": 50,
  "total_matches": 7,
  "completed_matches": 7,
  "remaining_matches": 0,
  "completion_percentage": 100,
  "total_goals": 14,
  "avg_goals": 2.0,
  "rankings": [
    {
      "rank": 1,
      "name": "Alpha Squad",
      "wins": 3,
      "losses": 0,
      "points": 9,
      "goals_scored": 8,
      "goals_conceded": 2,
      "goal_difference": 6,
      "win_rate": 100.0
    }
  ]
}
```

---

## Security & Sensitive Data Policy

The REST API strictly avoids exposing sensitive account data:
- Password hashes and reset tokens are **never** exposed in any serializer.
- Third-party API keys, secrets, and Cloudinary credentials are **never** returned.
- Internal SOLO team identifiers (`__SOLO_INTERNAL__`, `__SOLO_...`) are filtered out by property display methods.

