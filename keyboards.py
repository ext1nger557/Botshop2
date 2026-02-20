from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

CHANNEL_LINK = "https://t.me/+C8EqPbH5Dok5NWQy"


# ==================== MAIN MENU ====================
def get_main_keyboard(user_id: int, is_admin: bool) -> ReplyKeyboardMarkup:
    """Главное меню бота"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🛍️ Каталог"), KeyboardButton(text="🛒 Корзина"))
    builder.row(KeyboardButton(text="🎁 Бонусы"))
    if is_admin:
        builder.row(KeyboardButton(text="⚙️ Админ-панель"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка Назад (inline)"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu:main"))
    return builder.as_markup()


def get_back_reply_keyboard() -> ReplyKeyboardMarkup:
    """Кнопка Назад (reply)"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🔙 Назад в меню"))
    return builder.as_markup(resize_keyboard=True)


# ==================== CATALOG ====================
def get_products_keyboard(products: list, page: int = 0, page_size: int = 5) -> InlineKeyboardMarkup:
    """Клавиатура каталога товаров"""
    builder = InlineKeyboardBuilder()
    start = page * page_size
    end = start + page_size

    for product in products[start:end]:
        btn_text = f"{product['name']} - {product['price']}₽ (📦{product['stock']})"
        builder.row(InlineKeyboardButton(
            text=btn_text,
            callback_data=f"product:{product['id']}"
        ))

    # Пагинация
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"catalog:page:{page - 1}"))
    if end < len(products):
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"catalog:page:{page + 1}"))
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu:main"))
    return builder.as_markup()


def get_product_keyboard(product_id: int, stock: int, in_cart: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура товара с кнопками +/-"""
    builder = InlineKeyboardBuilder()

    # Кнопки управления количеством
    btn_row = []

    # Кнопка Минус (активна только если что-то в корзине)
    if in_cart > 0:
        btn_row.append(InlineKeyboardButton(
            text="➖",
            callback_data=f"cart:dec:{product_id}"
        ))
    else:
        btn_row.append(InlineKeyboardButton(
            text="⚪",
            callback_data="noop"
        ))

    # Отображение количества в корзине
    btn_row.append(InlineKeyboardButton(
        text=f"🛒 {in_cart}" if in_cart > 0 else "🛒 0",
        callback_data="noop"
    ))

    # Кнопка Плюс (активна только если есть товар на складе)
    if stock > 0:
        btn_row.append(InlineKeyboardButton(
            text="➕",
            callback_data=f"cart:add:{product_id}"
        ))
    else:
        btn_row.append(InlineKeyboardButton(
            text="❌",
            callback_data="noop"
        ))

    builder.row(*btn_row)

    # Кнопка "В каталог"
    builder.row(InlineKeyboardButton(text="🔙 В каталог", callback_data="catalog:page:0"))

    return builder.as_markup()


# ==================== CART ====================
def get_cart_keyboard(cart_items: list) -> InlineKeyboardMarkup:
    """Клавиатура корзины"""
    builder = InlineKeyboardBuilder()

    for item in cart_items:
        builder.row(InlineKeyboardButton(
            text=f"❌ {item['name']} ({item['quantity']}шт)",
            callback_data=f"cart:remove:{item['product_id']}"
        ))

    builder.row(InlineKeyboardButton(text="✅ Оформить заказ", callback_data="order:checkout"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu:main"))
    return builder.as_markup()


def get_checkout_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура оформления заказа"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 Оплатить", callback_data="order:pay"))
    builder.row(InlineKeyboardButton(text="🔙 Вернуться в корзину", callback_data="menu:cart"))
    return builder.as_markup()


def get_payment_keyboard(order_number: str) -> InlineKeyboardMarkup:
    """Клавиатура после оплаты"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="📩 Написать админу",
        url="https://t.me/romasha_1"
    ))
    builder.row(InlineKeyboardButton(text="🔙 В главное меню", callback_data="menu:main"))
    return builder.as_markup()



# ==================== BONUSES ====================
def get_bonuses_keyboard(bonuses: list, has_active: bool) -> InlineKeyboardMarkup:
    """Клавиатура бонусов"""
    builder = InlineKeyboardBuilder()

    for bonus in bonuses:
        status = "✅ Активна" if bonus['is_active'] else "❌ Использована"
        builder.row(InlineKeyboardButton(
            text=f"🎁 Скидка {bonus['discount_percent']}% - {status}",
            callback_data=f"bonus:toggle:{bonus['id']}" if bonus['is_active'] else "noop"
        ))

    if has_active:
        builder.row(InlineKeyboardButton(
            text="🎯 Применить скидку к заказу",
            callback_data="bonus:apply"
        ))

    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu:main"))
    return builder.as_markup()


# ==================== ADMIN PANEL ====================
def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура админ-панели"""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="➕ Добавить товар"), KeyboardButton(text="📦 Пополнить товар"))
    builder.row(KeyboardButton(text="🗑️ Удалить товар"), KeyboardButton(text="💰 Изменить цену"))
    builder.row(KeyboardButton(text="👥 Список админов"), KeyboardButton(text="🎁 Система бонусов"))
    builder.row(KeyboardButton(text="🚫 ЧС пользователей"), KeyboardButton(text="📋 История заказов"))
    builder.row(KeyboardButton(text="🔙 В главное меню"))
    return builder.as_markup(resize_keyboard=True)


def get_admin_products_stock_keyboard(products: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора товара для пополнения (список товаров)"""
    builder = InlineKeyboardBuilder()

    for product in products:
        builder.row(InlineKeyboardButton(
            text=f"{product['name']} (📦{product['stock']})",
            callback_data=f"admin:stock:product:{product['id']}"
        ))

    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin:menu"))
    return builder.as_markup()


def get_admin_stock_keyboard(product_id: int, stock: int) -> InlineKeyboardMarkup:
    """Клавиатура управления остатком товара (+/-)"""
    builder = InlineKeyboardBuilder()

    # Кнопки +/-
    btn_row = []

    # Кнопка Минус
    if stock > 0:
        btn_row.append(InlineKeyboardButton(
            text="➖",
            callback_data=f"admin:stock:dec:{product_id}"
        ))
    else:
        btn_row.append(InlineKeyboardButton(
            text="⛔",
            callback_data="noop"
        ))

    # Отображение текущего количества
    btn_row.append(InlineKeyboardButton(
        text=f"📦 {stock}",
        callback_data="noop"
    ))

    # Кнопка Плюс
    btn_row.append(InlineKeyboardButton(
        text="➕",
        callback_data=f"admin:stock:add:{product_id}"
    ))

    builder.row(*btn_row)

    # Кнопки навигации
    builder.row(InlineKeyboardButton(text="🔙 К товарам", callback_data="admin:stock:menu"))
    builder.row(InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin:menu"))

    return builder.as_markup()


def get_admin_products_delete_keyboard(products: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора товара для удаления"""
    builder = InlineKeyboardBuilder()

    for product in products:
        builder.row(InlineKeyboardButton(
            text=f"{product['name']} (📦{product['stock']})",
            callback_data=f"admin:delete:product:{product['id']}"
        ))

    builder.row(InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin:menu"))
    return builder.as_markup()

def get_admin_product_actions(product_id: int) -> InlineKeyboardMarkup:
    """Действия с товаром для админа"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"admin:product:delete:{product_id}"),
        InlineKeyboardButton(text="💰 Цена", callback_data=f"admin:product:price:{product_id}")
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin:products"))
    return builder.as_markup()


def get_admin_users_keyboard(users: list, action: str) -> InlineKeyboardMarkup:
    """Клавиатура для работы с пользователями (админы/ЧС)"""
    builder = InlineKeyboardBuilder()
    for user in users:
        name = user.get('username') or user.get('first_name') or str(user['user_id'])
        builder.row(InlineKeyboardButton(
            text=f"{name} ({user['user_id']})",
            callback_data=f"admin:{action}:{user['user_id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin:menu"))
    return builder.as_markup()


def get_admin_bonuses_keyboard(users: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора пользователя для бонусов"""
    builder = InlineKeyboardBuilder()
    for user in users:
        name = user.get('username') or user.get('first_name') or str(user['user_id'])
        builder.row(InlineKeyboardButton(
            text=f"🎁 {name} ({user['user_id']})",
            callback_data=f"admin:bonus:user:{user['user_id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin:menu"))
    return builder.as_markup()


def get_bonus_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Действия с бонусами пользователя"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить скидку", callback_data=f"admin:bonus:add:{user_id}"),
        InlineKeyboardButton(text="📋 Мои скидки", callback_data=f"admin:bonus:list:{user_id}")
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin:bonuses"))
    return builder.as_markup()


def get_orders_keyboard(orders: list) -> InlineKeyboardMarkup:
    """Клавиатура списка заказов"""
    builder = InlineKeyboardBuilder()
    for order in orders[:10]:  # Последние 10 заказов
        status_emoji = {"pending": "⏳", "paid": "✅", "cancelled": "❌"}.get(order['status'], "📦")
        builder.row(InlineKeyboardButton(
            text=f"{status_emoji} {order['order_number']} | {order['final_price']}₽",
            callback_data=f"admin:order:{order['order_number']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin:menu"))
    return builder.as_markup()


def get_order_admin_keyboard(order_number: str) -> InlineKeyboardMarkup:
    """Клавиатура управления заказом"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin:order:confirm:{order_number}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data=f"admin:order:cancel:{order_number}")
    )
    builder.row(InlineKeyboardButton(text="🔙 К заказам", callback_data="admin:orders"))
    return builder.as_markup()