import os
import logging
from datetime import datetime
from typing import List, Dict, Optional  # ✅ Добавьте эту строку!

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from dotenv import load_dotenv

import database as db
import keyboards as kb
#Загрузка токена из .env и проверка

load_dotenv()

# Настройки
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))  # Главный админ
CHANNEL_LINK = "https://t.me/+C8EqPbH5Dok5NWQy"
PAYMENT_PHONE = "+79122127547"
PAYMENT_BANK = "Озонбанк"
SUPPORT_USERNAME = "@romasha_1"

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Проверьте файл .env")

print(f"✅ Токен загружен: {BOT_TOKEN[:20]}...")  # Показываем первые 20 символов

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ==================== FSM STATES ====================
class AdminStates(StatesGroup):
    adding_product = State()
    adding_stock = State()
    deleting_product = State()
    changing_price = State()
    adding_admin = State()
    removing_admin = State()
    adding_bonus = State()
    ban_user = State()
    unban_user = State()



# ==================== HANDLERS ====================

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    logging.info(f"📩 Получена команда /start от пользователя {message.from_user.id}")

    try:
        if await check_banned(message):
            logging.warning(f"Пользователь {message.from_user.id} в бане")
            return

        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name

        logging.info(f"Создаем/обновляем пользователя: {user_id}")
        await db.get_or_create_user(user_id, username, first_name)
        is_admin = await db.is_admin(user_id) or (user_id == ADMIN_ID)

        welcome_text = (
            f"👋 Привет, {first_name}!\n\n"
            f"🛍️ Добро пожаловать в наш Telegram-магазин!\n\n"
            f"🔥 <b>Подпишитесь на наш канал:</b>\n"
            f"👉 {CHANNEL_LINK}\n\n"
            f"Здесь вы найдете эксклюзивные товары по лучшим ценам! 🎁"
        )

        logging.info(f"Отправляем приветственное сообщение пользователю {user_id}")
        await message.answer(
            welcome_text,
            reply_markup=kb.get_main_keyboard(user_id, is_admin),
            parse_mode="HTML"
        )
        logging.info(f"✅ Сообщение отправлено пользователю {user_id}")

    except Exception as e:
        logging.error(f"❌ Ошибка в /start: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Попробуйте позже.")


@dp.message(F.text == "🔙 Назад в меню")
async def back_to_menu(message: types.Message, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    is_admin = await db.is_admin(message.from_user.id)
    await message.answer(
        "📋 Главное меню:",
        reply_markup=kb.get_main_keyboard(message.from_user.id, is_admin)
    )


@dp.message(F.text == "🛍️ Каталог")
async def show_catalog(message: types.Message):
    """Отображение каталога товаров"""
    if await check_banned(message):
        return

    products = await db.get_all_products()

    if not products:
        await message.answer("📭 Каталог пока пуст. Заходите позже!", reply_markup=kb.get_back_keyboard())
        return

    await message.answer(
        "🛍️ <b>Каталог товаров:</b>\n\nВыберите товар для просмотра:",
        reply_markup=kb.get_products_keyboard(products),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "catalog:page:0")
async def back_to_catalog(callback: types.CallbackQuery):
    """Возврат в каталог"""
    products = await db.get_all_products()

    if not products:
        await callback.message.edit_text("📭 Каталог пока пуст.")
        await callback.answer()
        return

    await callback.message.edit_text(
        "🛍️ <b>Каталог товаров:</b>\n\nВыберите товар для просмотра:",
        reply_markup=kb.get_products_keyboard(products, page=0),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("product:"))
async def show_product(callback: types.CallbackQuery):
    """Показ деталей товара с учетом товаров в корзине"""
    product_id = int(callback.data.split(":")[1])
    product = await db.get_product(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    # Проверяем, есть ли товар в корзине пользователя
    cart = await db.get_cart(callback.from_user.id)
    cart_item = next((item for item in cart if item['product_id'] == product_id), None)
    in_cart = cart_item['quantity'] if cart_item else 0

    # 🔄 Вычисляем доступный остаток (с учетом корзины)
    available_stock = product['stock'] - in_cart

    text = (
        f"📦 <b>{product['name']}</b>\n\n"
        f"📝 {product['description'] or 'Описание отсутствует'}\n\n"
        f"💰 Цена: <b>{product['price']}₽</b>\n"
        f"📦 В наличии: <b>{available_stock} шт.</b>\n"
    )

    if in_cart > 0:
        text += f"🛒 <b>В вашей корзине: {in_cart} шт.</b>\n"

    await callback.message.edit_text(
        text,
        reply_markup=kb.get_product_keyboard(product_id, available_stock, in_cart),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("cart:add:"))
async def cart_add(callback: types.CallbackQuery):
    """Добавление товара в корзину (+)"""
    parts = callback.data.split(":")
    product_id = int(parts[2])

    product = await db.get_product(product_id)
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    user_id = callback.from_user.id

    # Проверяем, сколько уже в корзине
    cart = await db.get_cart(user_id)
    cart_item = next((item for item in cart if item['product_id'] == product_id), None)
    current_in_cart = cart_item['quantity'] if cart_item else 0

    # 🔄 Проверяем доступный остаток (с учетом уже добавленного)
    available_stock = product['stock'] - current_in_cart

    if available_stock <= 0:
        await callback.answer("⚠️ Товар закончился!", show_alert=True)
        return

    # Добавляем в корзину (БЕЗ изменения остатка в БД)
    success = await db.add_to_cart(user_id, product_id, 1)
    if not success:
        await callback.answer("⚠️ Ошибка добавления в корзину", show_alert=True)
        return

    await callback.answer("✅ Товар добавлен!", show_alert=False)

    # 🔄 Обновляем сообщение (покажет новый доступный остаток)
    await update_product_message(callback, product_id)


@dp.callback_query(F.data.startswith("cart:dec:"))
async def cart_decrease(callback: types.CallbackQuery):
    """Уменьшение количества товара в корзине (-)"""
    parts = callback.data.split(":")
    product_id = int(parts[2])

    user_id = callback.from_user.id

    # Проверяем, есть ли в корзине
    cart = await db.get_cart(user_id)
    cart_item = next((item for item in cart if item['product_id'] == product_id), None)

    if not cart_item or cart_item['quantity'] <= 0:
        await callback.answer("❌ Товар не в корзине", show_alert=True)
        return

    # Уменьшаем количество
    new_qty = cart_item['quantity'] - 1

    if new_qty <= 0:
        # Удаляем из корзины
        await db.remove_from_cart(user_id, product_id)
    else:
        # Обновляем количество
        await db.update_cart_quantity(user_id, product_id, new_qty)

    await callback.answer("✅ Количество уменьшено", show_alert=False)

    # 🔄 Обновляем сообщение (покажет восстановленный остаток)
    await update_product_message(callback, product_id)


async def update_product_message(callback: types.CallbackQuery, product_id: int):
    """🔄 Обновление сообщения с товаром (с учетом корзины)"""
    # Получаем данные о товаре
    product = await db.get_product(product_id)
    if not product:
        return

    # Проверяем, есть ли товар в корзине
    cart = await db.get_cart(callback.from_user.id)
    cart_item = next((item for item in cart if item['product_id'] == product_id), None)
    in_cart = cart_item['quantity'] if cart_item else 0

    # 🔄 Вычисляем доступный остаток (с учетом корзины)
    available_stock = product['stock'] - in_cart

    # Формируем текст
    text = (
        f"📦 <b>{product['name']}</b>\n\n"
        f"📝 {product['description'] or 'Описание отсутствует'}\n\n"
        f"💰 Цена: <b>{product['price']}₽</b>\n"
        f"📦 В наличии: <b>{available_stock} шт.</b>\n"
    )

    if in_cart > 0:
        text += f"🛒 <b>В вашей корзине: {in_cart} шт.</b>\n"

    # Обновляем сообщение с новой клавиатурой
    try:
        await callback.message.edit_text(
            text,
            reply_markup=kb.get_product_keyboard(product_id, available_stock, in_cart),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.debug(f"Не удалось обновить сообщение: {e}")


@dp.message(F.text == "🛒 Корзина")
async def show_cart(message: types.Message):
    """Отображение корзины"""
    if await check_banned(message):
        return

    user_id = message.from_user.id
    cart = await db.get_cart(user_id)

    if not cart:
        await message.answer("🛒 Ваша корзина пуста", reply_markup=kb.get_back_keyboard())
        return

    total = sum(item['price'] * item['quantity'] for item in cart)

    text = "🛒 <b>Ваша корзина:</b>\n\n"
    for item in cart:
        subtotal = item['price'] * item['quantity']
        text += f"• {item['name']} × {item['quantity']} шт. = <b>{subtotal}₽</b>\n"
    text += f"\n💰 <b>Итого: {total}₽</b>"

    await message.answer(text, reply_markup=kb.get_cart_keyboard(cart), parse_mode="HTML")


@dp.callback_query(F.data == "cart:clear")
async def cart_clear(callback: types.CallbackQuery):
    """Очистка корзины"""
    await db.clear_cart(callback.from_user.id)
    await callback.answer("🧹 Корзина очищена")
    await callback.message.edit_text("🛒 Ваша корзина пуста", reply_markup=kb.get_back_keyboard())


@dp.callback_query(F.data == "order:checkout")
async def order_checkout(callback: types.CallbackQuery):
    """Оформление заказа - предпросмотр"""
    user_id = callback.from_user.id
    cart = await db.get_cart(user_id)

    if not cart:
        await callback.answer("Корзина пуста!", show_alert=True)
        return

    total = sum(item['price'] * item['quantity'] for item in cart)
    bonus = await db.get_active_bonus(user_id)

    text = "📋 <b>Ваш заказ:</b>\n\n"
    for item in cart:
        subtotal = item['price'] * item['quantity']
        text += f"• {item['name']} × {item['quantity']} = <b>{subtotal}₽</b>\n"

    text += f"\n💰 Сумма: <b>{total}₽</b>"

    if bonus:
        discount = total * bonus // 100
        final = total - discount
        text += f"\n🎁 Скидка {bonus}%: -{discount}₽"
        text += f"\n✅ <b>К оплате: {final}₽</b>"
    else:
        text += f"\n✅ <b>К оплате: {total}₽</b>"

    await callback.message.edit_text(text, reply_markup=kb.get_checkout_keyboard(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "order:pay")
async def order_pay(callback: types.CallbackQuery):
    """Оплата заказа"""
    user_id = callback.from_user.id
    cart = await db.get_cart(user_id)

    if not cart:
        await callback.answer("Корзина пуста!", show_alert=True)
        return

    # Получаем активный бонус
    bonus = await db.get_active_bonus(user_id)

    # Создаем заказ
    order_number = await db.create_order(user_id, cart, bonus or 0)

    if not order_number:
        await callback.answer("❌ Ошибка создания заказа", show_alert=True)
        return

    # Деактивация бонуса после использования
    if bonus:
        await db.deactivate_bonus(user_id)

    # Очистка корзины
    await db.clear_cart(user_id)

    # 🔔 ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ АДМИНАМ
    total = sum(item['price'] * item['quantity'] for item in cart)
    final = total - (total * (bonus or 0) // 100)

    await notify_admins_about_order(
        order_number=order_number,
        user_id=user_id,
        total=total,
        final=final,
        discount=bonus or 0,
        cart=cart
    )

    # Формирование сообщения для пользователя
    payment_text = (
        f"✅ <b>Заказ #{order_number} создан!</b>\n\n"
        f"💳 <b>Оплата переводом:</b>\n"
        f"Переведите сумму на номер:\n"
        f"📱 <code>+79122127547</code> (Озонбанк)\n\n"
        f"💰 Сумма к оплате: <b>{final}₽</b>\n\n"
        f"После перевода напишите @romasha_1 номер заказа "
        f"и прикрепите чек оплаты.\n\n"
        f"📦 Ваш заказ будет обработан после подтверждения оплаты!"
    )

    try:
        await callback.message.edit_text(
            payment_text,
            reply_markup=kb.get_payment_keyboard(order_number),
            parse_mode="HTML"
        )
    except:
        await callback.message.answer(
            payment_text,
            reply_markup=kb.get_payment_keyboard(order_number),
            parse_mode="HTML"
        )

    await callback.answer()

    # Рекламное сообщение после заказа
    await callback.message.answer(
        f"🙏 Спасибо за ваш заказ!\n\n"
        f"🔥 Не забудьте подписаться на наш канал:\n"
        f"👉 https://t.me/+C8EqPbH5Dok5NWQy\n\n"
        f"Там вас ждут эксклюзивные предложения! 🎁"
    )


@dp.message(F.text == "🎁 Бонусы")
async def show_bonuses(message: types.Message):
    """Отображение бонусов пользователя"""
    if await check_banned(message):
        return

    user_id = message.from_user.id
    bonuses = await db.get_user_bonuses(user_id)
    has_active = any(b['is_active'] for b in bonuses)

    if not bonuses:
        await message.answer(
            "🎁 У вас пока нет бонусов.\n"
            "Следите за акциями и участвуйте в розыгрышах!",
            reply_markup=kb.get_back_keyboard()
        )
        return

    text = "🎁 <b>Ваши бонусы:</b>\n\n"
    for bonus in bonuses:
        status = "✅ Активна" if bonus['is_active'] else "❌ Использована"
        text += f"• Скидка {bonus['discount_percent']}% - {status}\n"

    await message.answer(text, reply_markup=kb.get_bonuses_keyboard(bonuses, has_active), parse_mode="HTML")


@dp.callback_query(F.data == "bonus:apply")
async def bonus_apply(callback: types.CallbackQuery):
    """Применение бонуса к заказу"""
    await callback.answer("🎁 Скидка будет применена при оформлении заказа!", show_alert=True)


# ==================== ADMIN PANEL ====================

@dp.message(F.text == "⚙️ Админ-панель")
async def admin_panel(message: types.Message):
    user_id = message.from_user.id

    # ✅ Проверяем И базу данных, И ADMIN_ID
    is_admin_db = await db.is_admin(user_id)
    is_main_admin = (user_id == ADMIN_ID)

    if not is_admin_db and not is_main_admin:
        await message.answer("🔐 Доступ запрещен. Вы не администратор.")
        return

    # Если это главный админ (ADMIN_ID), но его нет в БД — добавляем
    if is_main_admin and not is_admin_db:
        await db.add_admin(user_id)
        logging.info(f"✅ Главный админ {user_id} добавлен в базу данных")

    await message.answer(
        "⚙️ <b>Панель администратора</b>\n\nВыберите действие:",
        reply_markup=kb.get_admin_keyboard(),
        parse_mode="HTML"
    )


@dp.message(F.text == "🔙 В главное меню")
async def admin_back_to_main(message: types.Message, state: FSMContext):
    """Возврат из админ-панели в главное меню"""
    # Очищаем состояние (если было активно)
    await state.clear()

    # Проверяем, админ ли пользователь
    is_admin = await db.is_admin(message.from_user.id) or (message.from_user.id == ADMIN_ID)

    # Отправляем главное меню
    await message.answer(
        "📋 Главное меню:",
        reply_markup=kb.get_main_keyboard(message.from_user.id, is_admin)
    )

@dp.message(F.text == "➕ Добавить товар")
async def admin_add_product_start(message: types.Message, state: FSMContext):
    """Начало добавления товара"""
    if not await db.is_admin(message.from_user.id):
        return

    await message.answer(
        "📝 Введите название товара:",
        reply_markup=kb.get_back_reply_keyboard()
    )
    await state.update_data(step="name")
    await state.set_state(AdminStates.adding_product)


@dp.message(AdminStates.adding_product)
async def admin_add_product_process(message: types.Message, state: FSMContext):
    """Процесс добавления товара"""
    data = await state.get_data()
    step = data.get("step")

    if step == "name":
        await state.update_data(name=message.text, step="description")
        await message.answer("📝 Введите описание товара:")

    elif step == "description":
        await state.update_data(description=message.text, step="price")
        await message.answer("💰 Введите цену товара (в рублях):")

    elif step == "price":
        if not message.text.isdigit():
            await message.answer("❌ Введите корректное число:")
            return
        await state.update_data(price=int(message.text), step="stock")
        await message.answer("📦 Введите количество товара:")

    elif step == "stock":
        if not message.text.isdigit():
            await message.answer("❌ Введите корректное число:")
            return

        data = await state.get_data()
        success = await db.add_product(
            name=data['name'],
            description=data['description'],
            price=data['price'],
            stock=int(message.text)
        )

        if success:
            await message.answer(f"✅ Товар \"{data['name']}\" добавлен!", reply_markup=kb.get_admin_keyboard())
        else:
            await message.answer("❌ Товар с таким названием уже существует!", reply_markup=kb.get_admin_keyboard())

        await state.clear()


@dp.message(F.text == "🗑️ Удалить товар")
async def admin_delete_product_start(message: types.Message, state: FSMContext):
    """Начало удаления товара - показываем список товаров"""
    if not (await db.is_admin(message.from_user.id) or message.from_user.id == ADMIN_ID):
        return

    products = await db.get_all_products()
    if not products:
        await message.answer("📭 Нет товаров для удаления", reply_markup=kb.get_admin_keyboard())
        return

    await message.answer(
        "🗑️ <b>Выберите товар для удаления:</b>",
        reply_markup=kb.get_admin_products_delete_keyboard(products),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.deleting_product)


@dp.callback_query(F.data.startswith("admin:delete:product:"))
async def admin_delete_product_confirm(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение удаления товара"""
    product_id = int(callback.data.split(":")[3])
    product = await db.get_product(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    # Показываем информацию о товаре и спрашиваем подтверждение
    text = (
        f"🗑️ <b>Удаление товара</b>\n\n"
        f"📦 <b>{product['name']}</b>\n"
        f"📝 {product['description'] or 'Описание отсутствует'}\n"
        f"💰 Цена: {product['price']}₽\n"
        f"📊 Остаток: {product['stock']} шт.\n\n"
        f"⚠️ <b>Вы уверены, что хотите удалить этот товар?</b>\n"
        f"Это действие нельзя отменить!"
    )

    # Клавиатура с подтверждением
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"admin:delete:confirm:{product_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin:delete:cancel")
    )
    builder.row(InlineKeyboardButton(text="🔙 К товарам", callback_data="admin:delete:menu"))

    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("admin:delete:confirm:"))
async def admin_delete_product_execute(callback: types.CallbackQuery, state: FSMContext):
    """Фактическое удаление товара"""
    product_id = int(callback.data.split(":")[3])
    product = await db.get_product(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    # Удаляем товар
    await db.remove_product(product_id)

    await callback.answer(f"✅ Товар \"{product['name']}\" удалён!", show_alert=True)

    # Показываем обновлённый список товаров
    products = await db.get_all_products()

    if not products:
        await callback.message.edit_text(
            "📭 Нет товаров для удаления",
            reply_markup=kb.get_admin_keyboard()
        )
        await state.clear()
        return

    await callback.message.edit_text(
        "🗑️ <b>Выберите товар для удаления:</b>",
        reply_markup=kb.get_admin_products_delete_keyboard(products),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "admin:delete:cancel")
async def admin_delete_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Отмена удаления"""
    await callback.answer("❌ Удаление отменено", show_alert=False)

    products = await db.get_all_products()
    if not products:
        await callback.message.edit_text(
            "📭 Нет товаров для удаления",
            reply_markup=kb.get_admin_keyboard()
        )
        await state.clear()
        return

    await callback.message.edit_text(
        "🗑️ <b>Выберите товар для удаления:</b>",
        reply_markup=kb.get_admin_products_delete_keyboard(products),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "admin:delete:menu")
async def admin_delete_menu_back(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к меню удаления товаров"""
    products = await db.get_all_products()
    if not products:
        await callback.message.edit_text(
            "📭 Нет товаров для удаления",
            reply_markup=kb.get_admin_keyboard()
        )
        await state.clear()
        return

    await callback.message.edit_text(
        "🗑️ <b>Выберите товар для удаления:</b>",
        reply_markup=kb.get_admin_products_delete_keyboard(products),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(F.text == "📦 Пополнить товар")
async def admin_add_stock_start(message: types.Message, state: FSMContext):
    """Начало пополнения товара - показываем список товаров"""
    if not (await db.is_admin(message.from_user.id) or message.from_user.id == ADMIN_ID):
        return

    products = await db.get_all_products()
    if not products:
        await message.answer("📭 Нет товаров для пополнения", reply_markup=kb.get_admin_keyboard())
        return

    await message.answer(
        "📦 <b>Выберите товар для пополнения:</b>",
        reply_markup=kb.get_admin_products_stock_keyboard(products),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.adding_stock)


@dp.callback_query(F.data.startswith("admin:product:"))
async def admin_product_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка действий с товаром в админке"""
    parts = callback.data.split(":")
    action = parts[2]

    if action == "delete":
        product_id = int(parts[3])
        product = await db.get_product(product_id)
        await db.remove_product(product_id)
        await callback.answer(f"🗑️ Товар \"{product['name']}\" удалён")
        products = await db.get_all_products()
        await callback.message.edit_reply_markup(
            reply_markup=kb.get_admin_products_keyboard(products)
        )

    elif action == "price":
        product_id = int(parts[3])
        await state.update_data(product_id=product_id)
        await callback.message.answer("💰 Введите новую цену:")
        await state.set_state(AdminStates.changing_price)
        await callback.answer()

    elif len(parts) == 3 and parts[2].isdigit():
        # Выбор товара для действий
        product_id = int(parts[2])
        await callback.message.edit_reply_markup(
            reply_markup=kb.get_admin_product_actions(product_id)
        )
        await callback.answer()

    elif action == "add_stock":
        # Обработка пополнения через FSM
        pass


@dp.callback_query(F.data.startswith("admin:stock:product:"))
async def admin_stock_product_view(callback: types.CallbackQuery, state: FSMContext):
    """Просмотр информации о товаре для пополнения"""
    product_id = int(callback.data.split(":")[3])
    product = await db.get_product(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    # Сохраняем ID товара в состоянии
    await state.update_data(product_id=product_id, product_name=product['name'])

    text = (
        f"📦 <b>{product['name']}</b>\n\n"
        f"📝 {product['description'] or 'Описание отсутствует'}\n\n"
        f"💰 Цена: <b>{product['price']}₽</b>\n"
        f"📊 <b>Текущий остаток: {product['stock']} шт.</b>\n\n"
        f"Используйте кнопки ➕ и ➖ для изменения количества:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=kb.get_admin_stock_keyboard(product_id, product['stock']),
        parse_mode="HTML"
    )
    await callback.answer()

#-------------------------------------------------------------------------------------

@dp.callback_query(F.data.startswith("admin:stock:add:"))
async def admin_stock_add(callback: types.CallbackQuery, state: FSMContext):
    """Добавление 1 штуки к товару"""
    product_id = int(callback.data.split(":")[3])
    product = await db.get_product(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    # Добавляем 1 штуку
    await db.add_stock(product_id, 1)

    # Получаем обновленные данные
    updated_product = await db.get_product(product_id)

    await callback.answer(f"✅ Добавлено! Теперь: {updated_product['stock']} шт.", show_alert=False)

    # Обновляем сообщение
    text = (
        f"📦 <b>{updated_product['name']}</b>\n\n"
        f"📝 {updated_product['description'] or 'Описание отсутствует'}\n\n"
        f"💰 Цена: <b>{updated_product['price']}₽</b>\n"
        f"📊 <b>Текущий остаток: {updated_product['stock']} шт.</b>\n\n"
        f"Используйте кнопки ➕ и ➖ для изменения количества:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=kb.get_admin_stock_keyboard(product_id, updated_product['stock']),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("admin:stock:dec:"))
async def admin_stock_decrease(callback: types.CallbackQuery, state: FSMContext):
    """Удаление 1 штуки из товара"""
    product_id = int(callback.data.split(":")[3])
    product = await db.get_product(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    if product['stock'] <= 0:
        await callback.answer("⚠️ Нельзя удалить, остаток 0!", show_alert=True)
        return

    # Убираем 1 штуку
    await db.add_stock(product_id, -1)

    # Получаем обновленные данные
    updated_product = await db.get_product(product_id)

    await callback.answer(f"✅ Удалено! Теперь: {updated_product['stock']} шт.", show_alert=False)

    # Обновляем сообщение
    text = (
        f"📦 <b>{updated_product['name']}</b>\n\n"
        f"📝 {updated_product['description'] or 'Описание отсутствует'}\n\n"
        f"💰 Цена: <b>{updated_product['price']}₽</b>\n"
        f"📊 <b>Текущий остаток: {updated_product['stock']} шт.</b>\n\n"
        f"Используйте кнопки ➕ и ➖ для изменения количества:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=kb.get_admin_stock_keyboard(product_id, updated_product['stock']),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "admin:stock:menu")
async def admin_stock_menu_back(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к списку товаров для пополнения"""
    products = await db.get_all_products()
    if not products:
        await callback.message.edit_text("📭 Нет товаров для пополнения")
        await callback.answer()
        return

    await callback.message.edit_text(
        "📦 <b>Выберите товар для пополнения:</b>",
        reply_markup=kb.get_admin_products_stock_keyboard(products),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "admin:menu")
async def admin_menu_back(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в админ-панель"""
    await state.clear()

    # ✅ ПРАВИЛЬНО: Удаляем сообщение и отправляем новое с ReplyKeyboard
    await callback.message.delete()

    await callback.message.answer(
        "⚙️ <b>Панель администратора</b>\n\nВыберите действие:",
        reply_markup=kb.get_admin_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()

#--------------------------------------------------------------------------------------------------

@dp.message(AdminStates.changing_price)
async def admin_change_price(message: types.Message, state: FSMContext):
    """Изменение цены товара"""
    if not message.text.isdigit():
        await message.answer("❌ Введите корректное число:")
        return

    data = await state.get_data()
    product_id = data.get('product_id')

    if product_id:
        product = await db.get_product(product_id)
        await db.update_price(product_id, int(message.text))
        await message.answer(
            f"✅ Цена товара \"{product['name']}\" изменена на {message.text}₽",
            reply_markup=kb.get_admin_keyboard()
        )

    await state.clear()


@dp.message(F.text == "👥 Список админов")
async def admin_list(message: types.Message):
    """Список администраторов"""
    if not (await db.is_admin(message.from_user.id) or message.from_user.id == ADMIN_ID):
        return

    admins = await db.get_all_admins()

    if not admins:
        await message.answer("👥 Администраторов пока нет", reply_markup=kb.get_back_keyboard())
        return

    text = "👥 <b>Администраторы:</b>\n\n"
    for admin in admins:
        name = admin.get('username') or admin.get('first_name') or str(admin['user_id'])
        text += f"• {name} (ID: {admin['user_id']})\n"

    # ✅ ПРАВИЛЬНОЕ СОЗДАНИЕ КЛАВИАТУРЫ:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="➕ Добавить админа"))
    builder.row(KeyboardButton(text="➖ Удалить админа"))
    builder.row(KeyboardButton(text="🔙 Назад"))

    await message.answer(
        text,
        reply_markup=builder.as_markup(resize_keyboard=True),
        parse_mode="HTML"
    )


@dp.message(F.text == "➕ Добавить админа")
async def admin_add_admin_start(message: types.Message, state: FSMContext):
    """Добавление админа"""
    if not await db.is_admin(message.from_user.id):
        return

    await message.answer("🆔 Введите ID пользователя для добавления в админы:",
                         reply_markup=kb.get_back_reply_keyboard())
    await state.set_state(AdminStates.adding_admin)


@dp.message(AdminStates.adding_admin)
async def admin_add_admin_process(message: types.Message, state: FSMContext):
    """Процесс добавления админа"""
    if not message.text.isdigit():
        await message.answer("❌ Введите корректный ID:")
        return

    user_id = int(message.text)
    await db.add_admin(user_id)

    await message.answer(f"✅ Пользователь {user_id} добавлен в админы!", reply_markup=kb.get_admin_keyboard())
    await state.clear()


@dp.message(F.text == "➖ Удалить админа")
async def admin_remove_admin_start(message: types.Message, state: FSMContext):
    """Удаление админа"""
    if not await db.is_admin(message.from_user.id):
        return

    await message.answer("🆔 Введите ID пользователя для удаления из админов:",
                         reply_markup=kb.get_back_reply_keyboard())
    await state.set_state(AdminStates.removing_admin)


@dp.message(AdminStates.removing_admin)
async def admin_remove_admin_process(message: types.Message, state: FSMContext):
    """Процесс удаления админа"""
    if not message.text.isdigit():
        await message.answer("❌ Введите корректный ID:")
        return

    user_id = int(message.text)
    await db.remove_admin(user_id)

    await message.answer(f"✅ Пользователь {user_id} удалён из админов!", reply_markup=kb.get_admin_keyboard())
    await state.clear()


@dp.message(F.text == "🎁 Система бонусов")
async def admin_bonuses_menu(message: types.Message):
    """Меню системы бонусов"""
    if not await db.is_admin(message.from_user.id):
        return

    users = await db.get_all_users()
    await message.answer(
        "🎁 <b>Система бонусов</b>\n\nВыберите пользователя:",
        reply_markup=kb.get_admin_bonuses_keyboard(users),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("admin:bonus:user:"))
async def admin_bonus_user(callback: types.CallbackQuery):
    """Выбор пользователя для работы с бонусами"""
    user_id = int(callback.data.split(":")[3])
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_bonus_actions_keyboard(user_id)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("admin:bonus:add:"))
async def admin_bonus_add(callback: types.CallbackQuery, state: FSMContext):
    """Добавление бонуса пользователю"""
    target_user_id = int(callback.data.split(":")[3])
    await state.update_data(target_user_id=target_user_id)
    await callback.message.answer("🎁 Введите размер скидки в процентах (например, 10 для 10%):")
    await state.set_state(AdminStates.adding_bonus)
    await callback.answer()


@dp.message(AdminStates.adding_bonus)
async def admin_bonus_add_process(message: types.Message, state: FSMContext):
    """Процесс добавления бонуса"""
    if not message.text.isdigit() or not (0 <= int(message.text) <= 100):
        await message.answer("❌ Введите корректный процент (0-100):")
        return

    data = await state.get_data()
    target_user_id = data.get('target_user_id')

    if target_user_id:
        await db.add_bonus(target_user_id, int(message.text))
        await message.answer(
            f"✅ Скидка {message.text}% добавлена пользователю {target_user_id}!",
            reply_markup=kb.get_admin_keyboard()
        )

    await state.clear()


@dp.message(F.text == "🚫 ЧС пользователей")
async def admin_blacklist(message: types.Message):
    """Управление черным списком"""
    if not await db.is_admin(message.from_user.id):
        return

    banned = await db.get_banned_users()

    text = "🚫 <b>Черный список:</b>\n\n"
    if banned:
        for user in banned:
            name = user.get('username') or user.get('first_name') or str(user['user_id'])
            text += f"• {name} (ID: {user['user_id']})\n"
    else:
        text += "Пусто"

    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="➕ Добавить в ЧС"))
    builder.row(KeyboardButton(text="➖ Удалить из ЧС"))
    builder.row(KeyboardButton(text="🔙 Назад"))

    await message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="HTML")


@dp.message(F.text == "➕ Добавить в ЧС")
async def admin_ban_start(message: types.Message, state: FSMContext):
    """Добавление в ЧС"""
    if not await db.is_admin(message.from_user.id):
        return

    await message.answer("🆔 Введите ID пользователя для блокировки:", reply_markup=kb.get_back_reply_keyboard())
    await state.set_state(AdminStates.ban_user)


@dp.message(AdminStates.ban_user)
async def admin_ban_process(message: types.Message, state: FSMContext):
    """Процесс блокировки"""
    if not message.text.isdigit():
        await message.answer("❌ Введите корректный ID:")
        return

    user_id = int(message.text)
    await db.ban_user(user_id)

    await message.answer(f"✅ Пользователь {user_id} добавлен в ЧС!", reply_markup=kb.get_admin_keyboard())
    await state.clear()


@dp.message(F.text == "➖ Удалить из ЧС")
async def admin_unban_start(message: types.Message, state: FSMContext):
    """Удаление из ЧС"""
    if not (await db.is_admin(message.from_user.id) or message.from_user.id == ADMIN_ID):
        return

    await message.answer(
        "🆔 Введите ID пользователя для разблокировки:",
        reply_markup=kb.get_back_reply_keyboard()
    )
    await state.set_state(AdminStates.unban_user)


@dp.message(AdminStates.unban_user)
async def admin_unban_process(message: types.Message, state: FSMContext):
    """Процесс разблокировки"""
    if not message.text.isdigit():
        await message.answer("❌ Введите корректный ID:")
        return

    user_id = int(message.text)
    await db.unban_user(user_id)

    await message.answer(
        f"✅ Пользователь {user_id} удалён из ЧС!",
        reply_markup=kb.get_admin_keyboard()
    )
    await state.clear()

@dp.message(F.text == "📋 История заказов")
async def admin_orders(message: types.Message):
    """История заказов"""
    if not await db.is_admin(message.from_user.id):
        return

    orders = await db.get_all_orders()

    if not orders:
        await message.answer("📋 Заказов пока нет", reply_markup=kb.get_back_keyboard())
        return

    await message.answer(
        "📋 <b>История заказов:</b>\n\nВыберите заказ:",
        reply_markup=kb.get_orders_keyboard(orders),
        parse_mode="HTML"
    )





async def notify_admins_about_order(order_number: str, user_id: int,
                                    total: int, final: int,
                                    discount: int, cart: List[Dict]):
    """Отправка уведомления всем администраторам о новом заказе"""

    # Получаем всех админов
    admin_ids = await db.get_all_admin_ids()

    # Добавляем главного админа из ADMIN_ID
    if ADMIN_ID not in admin_ids:
        admin_ids.append(ADMIN_ID)

    # Формируем текст уведомления
    text = (
        f"🔔 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
        f"📋 <b>Заказ #{order_number}</b>\n"
        f"👤 <b>Заказчик:</b> ID {user_id}\n\n"
        f"<b>📦 Товары:</b>\n"
    )

    for item in cart:
        subtotal = item['price'] * item['quantity']
        text += f"• {item['name']} × {item['quantity']} шт. = {subtotal}₽\n"

    text += f"\n💰 <b>Сумма:</b> {total}₽\n"

    if discount > 0:
        text += f"🎁 <b>Скидка:</b> {discount}%\n"

    text += f"✅ <b>К оплате:</b> {final}₽\n\n"
    text += f"⏳ <b>Статус:</b> Ожидает оплаты"

    # Отправляем уведомление каждому админу (БЕЗ клавиатуры)
    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode="HTML"
                # ❌ Убрали reply_markup
            )
            logging.info(f"✅ Уведомление отправлено админу {admin_id}")
        except Exception as e:
            logging.error(f"❌ Не удалось отправить уведомление админу {admin_id}: {e}")


# ==================== УДАЛЕНИЕ ЗАКАЗА ====================

@dp.callback_query(F.data.startswith("admin:order:delete:confirm:"))
async def admin_order_delete_execute(callback: types.CallbackQuery):
    """Фактическое удаление заказа"""
    # Разбираем callback: admin:order:delete:confirm:ORDER-000001
    parts = callback.data.split(":")
    if len(parts) < 5:
        await callback.answer("❌ Ошибка формата", show_alert=True)
        return

    order_number = parts[4]
    logging.info(f"🗑️ Выполняем удаление: {order_number}")

    # Удаляем
    success = await db.delete_order(order_number)

    if success:
        logging.info(f"✅ Заказ {order_number} удалён")
        await callback.answer(f"✅ Заказ {order_number} удалён!", show_alert=True)

        # Получаем обновлённый список
        orders = await db.get_all_orders()

        if not orders:
            await callback.message.edit_text(
                "📋 Заказов пока нет",
                reply_markup=kb.get_back_keyboard()
            )
            return

        # Показываем обновлённый список
        await callback.message.edit_text(
            "📋 <b>История заказов:</b>\n\nВыберите заказ:",
            reply_markup=kb.get_orders_keyboard(orders),
            parse_mode="HTML"
        )
    else:
        logging.error(f"❌ Не удалось удалить {order_number}")
        await callback.answer("❌ Ошибка при удалении", show_alert=True)

@dp.callback_query(F.data.startswith("admin:order:delete:"))
async def admin_order_delete_confirm(callback: types.CallbackQuery):
    """Показ подтверждения удаления"""
    # Разбираем callback: admin:order:delete:ORDER-000001
    parts = callback.data.split(":")
    if len(parts) < 4:
        await callback.answer("❌ Ошибка формата", show_alert=True)
        return

    order_number = parts[3]

    # Проверяем, не confirm ли это (чтобы не зациклиться)
    if len(parts) > 4 and parts[4] == "confirm":
        return

    logging.info(f"🗑️ Запрошено удаление: {order_number}")

    # Получаем заказ
    order = await db.get_order(order_number)
    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    # Текст подтверждения
    text = (
        f"🗑️ <b>Удаление заказа</b>\n\n"
        f"📋 Заказ: <b>#{order_number}</b>\n"
        f"💰 Сумма: {order['final_price']}₽\n\n"
        f"⚠️ <b>Удалить этот заказ?</b>\n"
        f"Действие необратимо!"
    )

    # Кнопки
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"admin:order:delete:confirm:{order_number}"),
        InlineKeyboardButton(text="❌ Нет, отмена", callback_data=f"admin:order:{order_number}")
    )

    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()




@dp.callback_query(F.data.startswith("admin:order:cancel:"))
async def admin_order_cancel(callback: types.CallbackQuery):
    """Отмена заказа (меняет статус, но не удаляет)"""
    parts = callback.data.split(":")

    # Проверяем, что это не confirm удаления
    if len(parts) > 3 and parts[3] == "confirm":
        return

    order_number = parts[3]

    # Меняем статус на cancelled
    await db.update_order_status(order_number, "cancelled")

    await callback.answer(f"✅ Статус заказа изменён на cancelled", show_alert=False)

    # Обновляем информацию о заказе
    order = await db.get_order(order_number)

    if order:
        text = f"📦 <b>Заказ {order['order_number']}</b>\n"
        text += f"👤 Пользователь: {order.get('username') or order['user_id']}\n"
        text += f"📅 Дата: {order['created_at']}\n"
        text += f"📊 Статус: {order['status']}\n\n"
        text += "<b>Товары:</b>\n"

        for item in order['items']:
            text += f"• {item['product_name']} × {item['quantity']} = {item['subtotal']}₽\n"

        text += f"\n💰 Сумма: {order['total_price']}₽\n"
        if order['discount_percent']:
            text += f"🎁 Скидка {order['discount_percent']}%\n"
        text += f"✅ <b>К оплате: {order['final_price']}₽</b>"

        await callback.message.edit_text(
            text,
            reply_markup=kb.get_order_admin_keyboard(order_number),
            parse_mode="HTML"
        )

@dp.callback_query(F.data.startswith("admin:order:"))
async def admin_order_view(callback: types.CallbackQuery):
    """Просмотр заказа админом"""
    parts = callback.data.split(":")

    if len(parts) == 3 and parts[2] != "confirm" and parts[2] != "cancel":
        # Просмотр заказа
        order_number = parts[2]
        order = await db.get_order(order_number)

        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        text = f"📦 <b>Заказ {order['order_number']}</b>\n"
        text += f"👤 Пользователь: {order.get('username') or order['user_id']}\n"
        text += f"📅 Дата: {order['created_at']}\n"
        text += f"📊 Статус: {order['status']}\n\n"
        text += "<b>Товары:</b>\n"

        for item in order['items']:
            text += f"• {item['product_name']} × {item['quantity']} = {item['subtotal']}₽\n"

        text += f"\n💰 Сумма: {order['total_price']}₽\n"
        if order['discount_percent']:
            text += f"🎁 Скидка {order['discount_percent']}%\n"
        text += f"✅ <b>К оплате: {order['final_price']}₽</b>"

        await callback.message.edit_text(
            text,
            reply_markup=kb.get_order_admin_keyboard(order_number),
            parse_mode="HTML"
        )
        await callback.answer()

    elif len(parts) == 4:
        # Изменение статуса
        action = parts[2]
        order_number = parts[3]
        new_status = "paid" if action == "confirm" else "cancelled"

        await db.update_order_status(order_number, new_status)
        emoji = "✅" if action == "confirm" else "❌"
        await callback.answer(f"{emoji} Статус заказа изменён на {new_status}")

        orders = await db.get_all_orders()
        await callback.message.edit_reply_markup(reply_markup=kb.get_orders_keyboard(orders))

# ==================== CATCH ALL CALLBACKS ====================
@dp.callback_query(F.data == "menu:main")
async def menu_main(callback: types.CallbackQuery):
    """Возврат в главное меню из inline"""
    is_admin = await db.is_admin(callback.from_user.id)

    # Просто отправляем новое сообщение с ReplyKeyboard
    await callback.message.answer(
        "📋 Главное меню:",
        reply_markup=kb.get_main_keyboard(callback.from_user.id, is_admin)
    )

    # Удаляем сообщение с inline-кнопками
    await callback.message.delete()

    await callback.answer()


@dp.callback_query(F.data == "menu:cart")
async def menu_cart(callback: types.CallbackQuery):
    """Возврат в корзину"""
    await show_cart(callback.message)
    await callback.answer()


@dp.callback_query(F.data == "noop")
async def noop(callback: types.CallbackQuery):
    """Пустая обработка"""
    await callback.answer()



@dp.errors()
async def errors_handler(update: types.Update, exception: Exception):
    """Обработчик ошибок"""
    logging.error(f"❌ Ошибка: {exception}", exc_info=True)
    return True

# ==================== MIDDLEWARE ====================
@dp.message()
async def check_banned(message: types.Message):
    """Проверка пользователя в черном списке"""
    if await db.is_banned(message.from_user.id):
        await message.answer("🚫 Вы находитесь в черном списке бота.")
        return True
    return False


# ==================== RUN ====================


async def on_startup():
    logging.info("✅ Все handlers зарегистрированы")
    logging.info(f" Зарегистрировано handlers: {len(dp.message.handlers)}")

dp.startup.register(on_startup)


async def main():
    await db.init_db()
    logger.info("🤖 Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())