from django.db.models import Q
from apps.teams.models import TeamMember
from apps.tournaments.models import TournamentRegistration, Match, Tournament


def get_player_profile(*, user):
    """
    Computes complete player profile data including teams, matches, tournament history,
    wins/losses/win_rate, recent matches, and dynamically computed achievements.
    """

    memberships = (
        TeamMember.objects.filter(user=user, is_active=True)
        .exclude(team__description="__SOLO_INTERNAL__")
        .select_related("team")
        .order_by("-joined_at")
    )
    user_teams = [m.team for m in memberships]

    registrations = (
        TournamentRegistration.objects.filter(
            Q(team__in=user_teams)
            | Q(user=user)
            | Q(registered_by=user, tournament__participation_type=Tournament.ParticipationType.SOLO)
        )
        .select_related("tournament", "tournament__game", "team")
        .order_by("-registered_at")
    )

    tournaments_dict = {}
    for reg in registrations:
        if reg.tournament.id not in tournaments_dict:
            tournaments_dict[reg.tournament.id] = {
                "tournament": reg.tournament,
                "team": reg.team if reg.team and reg.team.description != "__SOLO_INTERNAL__" else None,
            }
    tournament_history = list(tournaments_dict.values())

    all_user_matches = list(
        Match.objects.filter(
            Q(team_one__in=user_teams) | Q(team_two__in=user_teams)
        )
        .select_related("round__tournament", "team_one", "team_two", "winner")
        .order_by("-id")
    )

    completed_matches = [
        m for m in all_user_matches if m.status == Match.Status.COMPLETED and m.team_one and m.team_two
    ]

    wins = sum(1 for m in completed_matches if m.winner in user_teams)
    losses = sum(
        1 for m in completed_matches if m.winner and m.winner not in user_teams
    )
    matches_played = len(completed_matches)

    win_rate = (
        round((wins / matches_played) * 100, 1)
        if matches_played > 0
        else 0.0
    )

    processed_recent_matches = []
    for match in all_user_matches[:10]:
        user_team_in_match = (
            match.team_one if match.team_one in user_teams else match.team_two
        )
        opponent = (
            match.team_two if match.team_one in user_teams else match.team_one
        )

        is_team_one = match.team_one == user_team_in_match
        user_score = (
            match.team_one_score if is_team_one else match.team_two_score
        )
        opponent_score = (
            match.team_two_score if is_team_one else match.team_one_score
        )
        is_winner = (
            (match.winner == user_team_in_match) if match.winner else False
        )

        processed_recent_matches.append(
            {
                "match": match,
                "tournament": match.round.tournament,
                "user_team": user_team_in_match,
                "opponent": opponent,
                "user_score": user_score,
                "opponent_score": opponent_score,
                "is_winner": is_winner,
                "is_completed": (match.status == Match.Status.COMPLETED),
            }
        )

    # Achievements computation
    achievements = []
    championship_count = Tournament.objects.filter(
        champion__in=user_teams
    ).count()
    if championship_count > 0:
        achievements.append(
            {
                "title": "Tournament Champion",
                "icon": "🏆",
                "badge_class": "bg-warning text-dark",
                "description": f"Won {championship_count} tournament championship(s)",
            }
        )

    if any(
        m.team_role
        in [TeamMember.TeamRole.MANAGER, TeamMember.TeamRole.IGL]
        for m in memberships
    ):
        achievements.append(
            {
                "title": "Team Leader",
                "icon": "🛡️",
                "badge_class": "bg-primary text-white",
                "description": "Serves as Team Manager or In-Game Leader",
            }
        )

    if matches_played >= 5:
        achievements.append(
            {
                "title": "Veteran Competitor",
                "icon": "⚡",
                "badge_class": "bg-info text-white",
                "description": f"Completed {matches_played} official matches",
            }
        )

    if win_rate >= 60.0 and matches_played >= 3:
        achievements.append(
            {
                "title": "Sharpshooter",
                "icon": "🎯",
                "badge_class": "bg-success text-white",
                "description": f"Maintained a high win rate of {win_rate}%",
            }
        )

    if len(tournament_history) >= 2:
        achievements.append(
            {
                "title": "Seasoned Contender",
                "icon": "🎮",
                "badge_class": "bg-secondary text-white",
                "description": f"Participated in {len(tournament_history)} tournaments",
            }
        )

    return {
        "player": user,
        "memberships": memberships,
        "user_teams": user_teams,
        "tournament_history": tournament_history,
        "wins": wins,
        "losses": losses,
        "matches_played": matches_played,
        "win_rate": win_rate,
        "recent_matches": processed_recent_matches,
        "achievements": achievements,
    }


import logging
import secrets
import string
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils import timezone
from .models import PasswordResetOTP

logger = logging.getLogger(__name__)


def send_password_reset_otp(*, email):
    """
    Generates a secure 6-digit numeric OTP and emails it to the user.
    Generic success response prevents account enumeration.
    """
    clean_email = email.strip().lower() if email else ""
    generic_success = {
        "success": True,
        "message": "If an account with this email exists, a 6-digit verification code has been sent.",
    }

    if not clean_email:
        return {"success": False, "message": "Email address is required."}

    User = get_user_model()
    user = User.objects.filter(email__iexact=clean_email, is_active=True).first()
    if not user:
        return generic_success

    now = timezone.now()

    # Rate limiting: restrict requests if OTP was sent within the last 60 seconds
    recent_otp = PasswordResetOTP.objects.filter(
        email__iexact=user.email,
        created_at__gte=now - timedelta(seconds=60),
    ).first()
    if recent_otp:
        return generic_success

    # Invalidate previous unused OTPs for this email
    PasswordResetOTP.objects.filter(email__iexact=user.email, is_used=False).update(is_used=True)

    # Generate 6-digit numeric OTP code
    otp_code = "".join(secrets.choice(string.digits) for _ in range(6))
    expires_at = now + timedelta(minutes=10)

    otp_record = PasswordResetOTP.objects.create(
        email=user.email,
        otp_code=otp_code,
        expires_at=expires_at,
    )

    subject = "GameArena Password Reset Code"
    message = (
        f"Hello {user.username},\n\n"
        f"Your 6-digit password reset verification code is:\n\n"
        f"  {otp_code}\n\n"
        f"This code will expire in 10 minutes.\n"
        f"If you did not request a password reset, please ignore this message.\n\n"
        f"GameArena Support Team"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@gamearena.com")

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as e:
        logger.exception("Failed to send password reset OTP email to %s: %s", user.email, e)
        otp_record.delete()
        return {
            "success": False,
            "message": "Failed to send verification email. Please try again later.",
        }

    return generic_success


def verify_password_reset_otp(*, email, code):
    """
    Verifies a 6-digit OTP code and returns a single-use secure reset token on success.
    """
    clean_email = email.strip().lower() if email else ""
    clean_code = str(code).strip() if code else ""

    if not clean_email or not clean_code or len(clean_code) != 6 or not clean_code.isdigit():
        return {"success": False, "message": "Invalid email or verification code format."}

    now = timezone.now()
    otp = PasswordResetOTP.objects.filter(
        email__iexact=clean_email,
        is_used=False,
        expires_at__gt=now,
    ).order_by("-created_at").first()

    if not otp:
        return {"success": False, "message": "Invalid or expired verification code."}

    if otp.attempts >= 5:
        otp.is_used = True
        otp.save(update_fields=["is_used"])
        return {"success": False, "message": "Too many failed attempts. Please request a new verification code."}

    otp.attempts += 1
    if not secrets.compare_digest(otp.otp_code, clean_code):
        otp.save(update_fields=["attempts"])
        return {"success": False, "message": "Invalid verification code."}

    reset_token = secrets.token_urlsafe(32)
    otp.is_used = True
    otp.reset_token = reset_token
    otp.save(update_fields=["attempts", "is_used", "reset_token"])

    return {
        "success": True,
        "message": "Verification code accepted.",
        "reset_token": reset_token,
    }


def reset_password_with_token(*, reset_token, new_password, confirm_password):
    """
    Resets the user's password using a verified single-use reset authorization token.
    """
    clean_token = str(reset_token).strip() if reset_token else ""
    if not clean_token:
        return {"success": False, "message": "Reset authorization token is required."}

    if new_password != confirm_password:
        return {"success": False, "message": "New password and confirmation password do not match."}

    now = timezone.now()
    # Token valid for 15 minutes after generation
    otp = PasswordResetOTP.objects.filter(
        reset_token=clean_token,
        created_at__gte=now - timedelta(minutes=15),
    ).first()

    if not otp:
        return {"success": False, "message": "Invalid or expired reset token."}

    User = get_user_model()
    user = User.objects.filter(email__iexact=otp.email, is_active=True).first()
    if not user:
        return {"success": False, "message": "Associated account not found."}

    try:
        validate_password(new_password, user=user)
    except ValidationError as e:
        return {"success": False, "message": " ".join(e.messages)}

    user.set_password(new_password)
    user.save()

    # Clear single-use reset token
    otp.reset_token = None
    otp.save(update_fields=["reset_token"])

    return {"success": True, "message": "Password changed successfully."}

