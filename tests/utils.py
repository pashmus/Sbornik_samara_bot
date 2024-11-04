from datetime import datetime
from aiogram.types import User, Chat, Message, CallbackQuery, Update

TEST_USER = User(id=1000, is_bot=False, first_name='testik', last_name='testovvv', username='ttt_vvv',
                 language_code='en-EN')

TEST_USER_CHAT = Chat(id=11, type='private', first_name=TEST_USER.first_name, last_name=TEST_USER.last_name,
                      username=TEST_USER.username)

def get_message(text: str) -> Message:
    return Message(message_id=123, date=datetime.now(), chat=TEST_USER_CHAT, from_user=TEST_USER,
                   sender_chat=TEST_USER_CHAT, text=text,
                   message_thread_id = None, sender_boost_count = None,
                   sender_business_bot = None, business_connection_id = None,
    forward_origin = None,
    is_topic_message = None, is_automatic_forward = None,
    reply_to_message = None, external_reply = None,
    quote = None, reply_to_story = None, via_bot = None,
    edit_date = None, has_protected_content = None, is_from_offline = None,
    media_group_id = None, author_signature = None, entities = None,
    link_preview_options = None, effect_id = None,
    animation = None, audio = None, document = None,
    paid_media = None, photo = None, sticker = None,
    story = None, video = None, video_note = None, voice = None,
    caption = None, caption_entities = None,
    show_caption_above_media = None, has_media_spoiler = None)
    #
    # contact: Contact | None = None, dice: Dice | None = None, game: Game | None = None,
    # poll: Poll | None = None, venue: Venue | None = None, location: Location | None = None,
    # new_chat_members: list[User] | None = None, left_chat_member: User | None = None,
    # new_chat_title: str | None = None, new_chat_photo: list[PhotoSize] | None = None,
    # delete_chat_photo: bool | None = None, group_chat_created: bool | None = None,
    # supergroup_chat_created: bool | None = None, channel_chat_created: bool | None = None,
    # message_auto_delete_timer_changed: MessageAutoDeleteTimerChanged | None = None,
    # migrate_to_chat_id: int | None = None, migrate_from_chat_id: int | None = None,
    # pinned_message: Message | InaccessibleMessage | None = None, invoice: Invoice | None = None,
    # successful_payment: SuccessfulPayment | None = None, refunded_payment: RefundedPayment | None = None,
    # users_shared: UsersShared | None = None, chat_shared: ChatShared | None = None, connected_website: str | None = None,
    # write_access_allowed: WriteAccessAllowed | None = None, passport_data: PassportData | None = None,
    # proximity_alert_triggered: ProximityAlertTriggered | None = None, boost_added: ChatBoostAdded | None = None,
    # chat_background_set: ChatBackground | None = None, forum_topic_created: ForumTopicCreated | None = None,
    # forum_topic_edited: ForumTopicEdited | None = None, forum_topic_closed: ForumTopicClosed | None = None,
    # forum_topic_reopened: ForumTopicReopened | None = None, general_forum_topic_hidden: GeneralForumTopicHidden | None = None,
    # general_forum_topic_unhidden: GeneralForumTopicUnhidden | None = None, giveaway_created: GiveawayCreated | None = None,
    # giveaway: Giveaway | None = None, giveaway_winners: GiveawayWinners | None = None,
    # giveaway_completed: GiveawayCompleted | None = None, video_chat_scheduled: VideoChatScheduled | None = None,
    # video_chat_started: VideoChatStarted | None = None, video_chat_ended: VideoChatEnded | None = None,
    # video_chat_participants_invited: VideoChatParticipantsInvited | None = None, web_app_data: WebAppData | None = None,
    # reply_markup: InlineKeyboardMarkup | None = None, forward_date: _datetime_serializer, return_type=int,
    # when_used=unless - none)] | None = None, forward_from: User | None = None, forward_from_chat: Chat | None = None,
    # forward_from_message_id: int | None = None, forward_sender_name: str | None = None, forward_signature: str | None = None,
    # user_shared: UserShared | None = None)

def get_update(message: Message = None, call: CallbackQuery = None):
    return Update(
        update_id=1234, message = message, edited_message = None, channel_post = None, edited_channel_post = None,
        business_connection = None, business_message = None, edited_business_message = None,
        deleted_business_messages = None, message_reaction = None, message_reaction_count = None,
        inline_query = None, chosen_inline_result = None, callback_query = call, shipping_query = None,
        pre_checkout_query = None, purchased_paid_media = None, poll = None, poll_answer = None, my_chat_member = None,
        chat_member = None, chat_join_request = None, chat_boost = None, removed_chat_boost = None)

