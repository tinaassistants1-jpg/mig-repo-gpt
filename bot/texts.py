"""Все тексты бота в одном месте — правятся без захода в логику."""

from __future__ import annotations

from html import escape

START = (
    "👋 Здравствуйте!\n\n"
    "Это бот приёма заявок. За пару минут я задам несколько вопросов "
    "и передам вашу задачу менеджеру — он свяжется с вами лично.\n\n"
    "Выберите действие ниже."
)

ABOUT = (
    "ℹ️ <b>О нас</b>\n\n"
    "Мы делаем сайты, веб-приложения, телеграм-ботов, дизайн и автоматизацию.\n"
    "Работаем от идеи до запуска: аналитика → дизайн → разработка → поддержка.\n\n"
    "Оставьте заявку — вернёмся с ответом в рабочее время."
)

SERVICES_INTRO = "🧩 <b>Наши услуги</b>\n\nВыберите направление, чтобы оставить заявку:"

ASK_SERVICE = "1/5 · Какая услуга вас интересует?"
ASK_BUDGET = "2/5 · Какой ориентировочный бюджет?"
ASK_DESCRIPTION = (
    "3/5 · Опишите задачу своими словами.\n\n"
    "Что нужно сделать, для кого, есть ли примеры или сроки — "
    "чем подробнее, тем точнее будет оценка."
)
ASK_NAME = "4/5 · Как к вам обращаться?"
ASK_CONTACT = (
    "5/5 · Оставьте контакт для связи.\n\n"
    "Нажмите кнопку ниже, чтобы поделиться номером, "
    "или пришлите телефон / e-mail / @username текстом."
)

CONFIRM_INTRO = "Проверьте заявку перед отправкой:"

LEAD_SAVED = (
    "✅ Заявка №{lead_id} принята!\n\n"
    "Менеджер свяжется с вами в рабочее время. "
    "Если появятся детали — просто отправьте новую заявку."
)

CANCELLED = "Отменено. Можно начать заново в любой момент — /start"
NOTHING_TO_CANCEL = "Сейчас нечего отменять. Начните с /start"

HELP = (
    "<b>Команды</b>\n"
    "/start — главное меню\n"
    "/lead — оставить заявку\n"
    "/cancel — отменить заполнение\n"
    "/help — эта справка"
)

ADMIN_HELP = (
    "<b>Команды администратора</b>\n"
    "/leads [статус] — последние заявки (new / in_work / done / rejected)\n"
    "/lead_info &lt;id&gt; — карточка заявки\n"
    "/status &lt;id&gt; &lt;статус&gt; — сменить статус\n"
    "/stats — сводка по заявкам\n"
    "/export — выгрузка всех заявок в CSV\n"
    "/audit — последние действия в журнале"
)

# ── Ошибки и подсказки ───────────────────────────────────────────────────

ERR_DESCRIPTION_SHORT = "Слишком коротко — опишите задачу хотя бы {min_len} символами."
ERR_DESCRIPTION_LONG = "Слишком длинно. Уложитесь, пожалуйста, в {max_len} символов."
ERR_NAME_INVALID = "Имя должно быть от {min_len} до {max_len} символов. Попробуйте ещё раз."
ERR_CONTACT_INVALID = (
    "Не похоже на контакт. Пришлите телефон (+7...), e-mail или @username, "
    "либо нажмите кнопку «Поделиться номером»."
)
ERR_EXPECTED_TEXT = "Пожалуйста, отправьте ответ текстом."
ERR_UNKNOWN = "Что-то пошло не так. Попробуйте ещё раз или начните с /start"
ERR_NOT_ADMIN = "Команда доступна только администраторам."
ERR_LEAD_NOT_FOUND = "Заявка №{lead_id} не найдена."
ERR_BAD_STATUS = "Неизвестный статус. Доступны: {statuses}"
ERR_BAD_USAGE = "Формат: <code>{usage}</code>"
ERR_THROTTLED = "Слишком часто. Подождите пару секунд 🙂"

NO_LEADS = "Заявок пока нет."


def lead_card(
    *,
    lead_id: int | None,
    service: str,
    budget: str,
    description: str,
    contact_name: str,
    contact_value: str,
    status: str | None = None,
    created_at: str | None = None,
    author: str | None = None,
) -> str:
    """Карточка заявки — используется и в подтверждении, и в админке."""
    head = f"<b>Заявка №{lead_id}</b>" if lead_id is not None else "<b>Ваша заявка</b>"
    lines = [head]
    if status:
        lines.append(f"Статус: {status}")
    # Всё, что пришло от пользователя, экранируем: сообщения уходят с parse_mode=HTML.
    lines += [
        f"Услуга: {escape(service)}",
        f"Бюджет: {escape(budget)}",
        f"Имя: {escape(contact_name)}",
        f"Контакт: {escape(contact_value)}",
        "",
        f"Задача:\n{escape(description)}",
    ]
    if author:
        lines += ["", f"От: {escape(author)}"]
    if created_at:
        lines.append(f"Создана: {created_at}")
    return "\n".join(lines)


def new_lead_notification(card: str) -> str:
    return f"🔔 <b>Новая заявка</b>\n\n{card}"
