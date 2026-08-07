from .models import Notification


def send_notification(
    *,
    recipient,
    title,
    message,
    notification_type=Notification.Type.SYSTEM,
):

    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
    )


def mark_notification_as_read(*, notification):
    """
    Marks a single notification as read.
    """
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])


def mark_all_notifications_as_read(*, user):
    """
    Marks all unread notifications for a user as read.
    """
    return Notification.objects.filter(
        recipient=user,
        is_read=False,
    ).update(is_read=True)


def get_unread_count(*, user):
    """
    Returns the count of unread notifications for a user.
    """
    if not user or not user.is_authenticated:
        return 0
    return Notification.objects.filter(
        recipient=user,
        is_read=False,
    ).count()
