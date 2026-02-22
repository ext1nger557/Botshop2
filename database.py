import aiosqlite
import logging  # ✅ Добавьте!
import os
from datetime import datetime
from typing import Optional, List, Dict
DB_PATH = "shop_bot.db"


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS users
                         (
                             user_id
                             INTEGER
                             PRIMARY
                             KEY,
                             username
                             TEXT,
                             first_name
                             TEXT,
                             is_admin
                             INTEGER
                             DEFAULT
                             0,
                             is_banned
                             INTEGER
                             DEFAULT
                             0,
                             created_at
                             TIMESTAMP
                             DEFAULT
                             CURRENT_TIMESTAMP
                         )
                         """)

        # Таблица товаров
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS products
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             name
                             TEXT
                             UNIQUE
                             NOT
                             NULL,
                             description
                             TEXT,
                             price
                             INTEGER
                             NOT
                             NULL,
                             stock
                             INTEGER
                             NOT
                             NULL,
                             created_at
                             TIMESTAMP
                             DEFAULT
                             CURRENT_TIMESTAMP
                         )
                         """)

        # Таблица корзины
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS cart
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             user_id
                             INTEGER
                             NOT
                             NULL,
                             product_id
                             INTEGER
                             NOT
                             NULL,
                             quantity
                             INTEGER
                             DEFAULT
                             1,
                             FOREIGN
                             KEY
                         (
                             user_id
                         ) REFERENCES users
                         (
                             user_id
                         ),
                             FOREIGN KEY
                         (
                             product_id
                         ) REFERENCES products
                         (
                             id
                         ),
                             UNIQUE
                         (
                             user_id,
                             product_id
                         )
                             )
                         """)

        # Таблица бонусов
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS bonuses
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             user_id
                             INTEGER
                             NOT
                             NULL,
                             discount_percent
                             INTEGER
                             NOT
                             NULL,
                             is_active
                             INTEGER
                             DEFAULT
                             1,
                             created_at
                             TIMESTAMP
                             DEFAULT
                             CURRENT_TIMESTAMP,
                             FOREIGN
                             KEY
                         (
                             user_id
                         ) REFERENCES users
                         (
                             user_id
                         )
                             )
                         """)

        # Таблица заказов
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS orders
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             order_number
                             TEXT
                             UNIQUE
                             NOT
                             NULL,
                             user_id
                             INTEGER
                             NOT
                             NULL,
                             total_price
                             INTEGER
                             NOT
                             NULL,
                             discount_percent
                             INTEGER
                             DEFAULT
                             0,
                             final_price
                             INTEGER
                             NOT
                             NULL,
                             status
                             TEXT
                             DEFAULT
                             'pending',
                             created_at
                             TIMESTAMP
                             DEFAULT
                             CURRENT_TIMESTAMP,
                             FOREIGN
                             KEY
                         (
                             user_id
                         ) REFERENCES users
                         (
                             user_id
                         )
                             )
                         """)

        # Таблица позиций заказа
        await db.execute("""
                         CREATE TABLE IF NOT EXISTS order_items
                         (
                             id
                             INTEGER
                             PRIMARY
                             KEY
                             AUTOINCREMENT,
                             order_id
                             INTEGER
                             NOT
                             NULL,
                             product_name
                             TEXT
                             NOT
                             NULL,
                             quantity
                             INTEGER
                             NOT
                             NULL,
                             price_per_item
                             INTEGER
                             NOT
                             NULL,
                             subtotal
                             INTEGER
                             NOT
                             NULL,
                             FOREIGN
                             KEY
                         (
                             order_id
                         ) REFERENCES orders
                         (
                             id
                         )
                             )
                         """)

        await db.execute("""
                         CREATE TABLE IF NOT EXISTS user_settings
                         (
                             user_id
                             INTEGER
                             PRIMARY
                             KEY,
                             use_bonus
                             INTEGER
                             DEFAULT
                             1,
                             FOREIGN
                             KEY
                         (
                             user_id
                         ) REFERENCES users
                         (
                             user_id
                         )
                             )
                         """)

        # ✅ Таблица настроек (для режима техработ)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        await db.commit()
    print("✅ База данных инициализирована")


# ==================== USERS ====================
async def get_or_create_user(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
                         INSERT
                         OR IGNORE INTO users (user_id, username, first_name) 
            VALUES (?, ?, ?)
                         """, (user_id, username, first_name))
        await db.commit()


async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()
        return result and result[0] == 1


async def is_banned(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()
        return result and result[0] == 1


async def add_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
        await db.commit()


async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_admin = 0 WHERE user_id = ?", (user_id,))
        await db.commit()


async def ban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        await db.commit()


async def unban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_all_admins() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT user_id, username, first_name FROM users WHERE is_admin = 1")
        return [dict(row) for row in await cursor.fetchall()]


async def get_all_users() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT user_id, username, first_name FROM users")
        return [dict(row) for row in await cursor.fetchall()]


async def get_banned_users() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT user_id, username, first_name FROM users WHERE is_banned = 1")
        return [dict(row) for row in await cursor.fetchall()]


# ==================== PRODUCTS ====================
async def add_product(name: str, description: str, price: int, stock: int) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                             INSERT INTO products (name, description, price, stock)
                             VALUES (?, ?, ?, ?)
                             """, (name, description, price, stock))
            await db.commit()
        return True
    except aiosqlite.IntegrityError:
        return False


async def add_stock(product_id: int, quantity: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
                         UPDATE products
                         SET stock = stock + ?
                         WHERE id = ?
                         """, (quantity, product_id))
        await db.commit()


#async def remove_product(product_id: int):
    #async with aiosqlite.connect(DB_PATH) as db:
        #await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        #await db.commit()

async def remove_product(product_id: int):
    """Удаление товара"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Сначала удаляем товар из корзин пользователей
        await db.execute("DELETE FROM cart WHERE product_id = ?", (product_id,))

        # ❌ УДАЛИТЬ эту строку (order_items не имеет product_id):
        # await db.execute("DELETE FROM order_items WHERE product_id = ?", (product_id,))

        # ✅ Вместо этого просто удаляем товар
        # Примечание: order_items хранит product_name, а не product_id
        # Поэтому исторические заказы сохранят информацию о товаре

        await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await db.commit()


async def update_price(product_id: int, new_price: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE products SET price = ? WHERE id = ?", (new_price, product_id))
        await db.commit()


async def get_all_products() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM products ORDER BY name")
        return [dict(row) for row in await cursor.fetchall()]


async def get_product(product_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        result = await cursor.fetchone()
        return dict(result) if result else None


async def get_product_by_name(name: str) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM products WHERE name = ?", (name,))
        result = await cursor.fetchone()
        return dict(result) if result else None


async def reduce_stock(product_id: int, quantity: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
                         UPDATE products
                         SET stock = stock - ?
                         WHERE id = ?
                           AND stock >= ?
                         """, (quantity, product_id, quantity))
        await db.commit()


# ==================== CART ====================
async def add_to_cart(user_id: int, product_id: int, quantity: int = 1):
    """Добавление товара в корзину (БЕЗ изменения остатка)"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем наличие товара
            cursor = await db.execute(
                "SELECT stock FROM products WHERE id = ?",
                (product_id,)
            )
            result = await cursor.fetchone()

            if not result or result[0] < quantity:
                return False

            # Добавляем или обновляем в корзине
            await db.execute("""
                             INSERT INTO cart (user_id, product_id, quantity)
                             VALUES (?, ?, ?) ON CONFLICT(user_id, product_id) 
                DO
                             UPDATE SET quantity = quantity + ?
                             """, (user_id, product_id, quantity, quantity))

            # ✅ НЕ УМЕНЬШАЕМ остаток! Только при оформлении заказа
            # await db.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))

            await db.commit()
            return True
    except Exception as e:
        logging.error(f"❌ Ошибка при добавлении в корзину: {e}")
        return False


async def get_cart(user_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
                                  SELECT c.*, p.name, p.price, p.stock
                                  FROM cart c
                                           JOIN products p ON c.product_id = p.id
                                  WHERE c.user_id = ?
                                  """, (user_id,))
        return [dict(row) for row in await cursor.fetchall()]


async def remove_from_cart(user_id: int, product_id: int):
    """Удаление товара из корзины (БЕЗ изменения остатка)"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # ✅ Просто удаляем товар из корзины
            # НЕ восстанавливаем остаток, так как при добавлении он не уменьшался
            await db.execute("""
                             DELETE
                             FROM cart
                             WHERE user_id = ?
                               AND product_id = ?
                             """, (user_id, product_id))

            await db.commit()

            logging.info(f"🗑️ Товар {product_id} удален из корзины пользователя {user_id}")
    except Exception as e:
        logging.error(f"❌ Ошибка при удалении из корзины: {e}")


async def clear_cart(user_id: int):
    """Очистка корзины пользователя (БЕЗ изменения остатка)"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # ✅ Просто удаляем все товары из корзины
            # НЕ восстанавливаем остаток, так как при добавлении он не уменьшался
            await db.execute("""
                             DELETE
                             FROM cart
                             WHERE user_id = ?
                             """, (user_id,))

            await db.commit()

            logging.info(f"🗑️ Корзина пользователя {user_id} очищена")
    except Exception as e:
        logging.error(f"❌ Ошибка при очистке корзины: {e}")


async def update_cart_quantity(user_id: int, product_id: int, quantity: int):
    """Обновление количества товара в корзине (БЕЗ изменения остатка)"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            if quantity <= 0:
                # Удаляем товар
                await db.execute("""
                                 DELETE
                                 FROM cart
                                 WHERE user_id = ?
                                   AND product_id = ?
                                 """, (user_id, product_id))
            else:
                # Обновляем количество
                await db.execute("""
                                 UPDATE cart
                                 SET quantity = ?
                                 WHERE user_id = ?
                                   AND product_id = ?
                                 """, (quantity, user_id, product_id))

            await db.commit()
    except Exception as e:
        logging.error(f"❌ Ошибка при обновлении количества: {e}")


async def update_price(product_id: int, new_price: int) -> bool:
    """Обновление цены товара"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE products SET price = ? WHERE id = ?
            """, (new_price, product_id))
            await db.commit()
            logging.info(f"💰 Цена товара ID={product_id} изменена на {new_price}₽")
            return True
    except Exception as e:
        logging.error(f"❌ Ошибка при изменении цены: {e}")
        return False

# ==================== BONUSES ====================
async def add_bonus(user_id: int, discount_percent: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
                         INSERT INTO bonuses (user_id, discount_percent, is_active)
                         VALUES (?, ?, 1)
                         """, (user_id, discount_percent))
        await db.commit()


async def get_active_bonus(user_id: int) -> Optional[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
                                  SELECT discount_percent
                                  FROM bonuses
                                  WHERE user_id = ?
                                    AND is_active = 1
                                  ORDER BY created_at DESC LIMIT 1
                                  """, (user_id,))
        result = await cursor.fetchone()
        return result[0] if result else None


async def deactivate_bonus(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
                         UPDATE bonuses
                         SET is_active = 0
                         WHERE user_id = ?
                           AND is_active = 1
                         """, (user_id,))
        await db.commit()


async def get_user_bonuses(user_id: int) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
                                  SELECT *
                                  FROM bonuses
                                  WHERE user_id = ?
                                  ORDER BY created_at DESC
                                  """, (user_id,))
        return [dict(row) for row in await cursor.fetchall()]


async def remove_bonus(bonus_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM bonuses WHERE id = ?", (bonus_id,))
        await db.commit()


# ==================== ORDERS ====================
async def create_order(user_id: int, cart_items: List[Dict],
                       discount_percent: int = 0) -> Optional[str]:
    """Создание заказа с возвратом номера заказа"""
    try:
        import uuid
        import time

        # ✅ Обрабатываем None значение скидки
        if discount_percent is None:
            discount_percent = 0

        async with aiosqlite.connect(DB_PATH) as db:
            # Подсчет суммы
            total_price = sum(item['price'] * item['quantity'] for item in cart_items)

            # ✅ Безопасный расчет скидки
            discount_percent = int(discount_percent) if discount_percent else 0
            final_price = total_price - (total_price * discount_percent // 100)

            logging.info(f"📋 Создаем заказ. Total: {total_price}, Discount: {discount_percent}%, Final: {final_price}")

            # Генерация уникального номера заказа
            timestamp = int(time.time()) % 1000000
            unique_id = str(uuid.uuid4())[:6].upper()
            order_number = f"ORDER-{timestamp}-{unique_id}"

            # Создание заказа
            await db.execute("""
                             INSERT INTO orders (order_number, user_id, total_price,
                                                 discount_percent, final_price, status)
                             VALUES (?, ?, ?, ?, ?, 'pending')
                             """, (order_number, user_id, total_price, discount_percent, final_price))

            # Получаем ID созданного заказа
            cursor = await db.execute("SELECT last_insert_rowid()")
            result = await cursor.fetchone()
            order_id = result[0]

            logging.info(f"✅ Заказ {order_number} создан с ID={order_id}")

            # Добавление позиций заказа
            for item in cart_items:
                subtotal = item['price'] * item['quantity']
                await db.execute("""
                                 INSERT INTO order_items (order_id, product_name, quantity,
                                                          price_per_item, subtotal)
                                 VALUES (?, ?, ?, ?, ?)
                                 """, (order_id, item['name'], item['quantity'],
                                       item['price'], subtotal))

                # Уменьшение остатка товара
                await db.execute("""
                                 UPDATE products
                                 SET stock = stock - ?
                                 WHERE id = ?
                                 """, (item['quantity'], item['product_id']))

            await db.commit()
            logging.info(f"✅ Заказ {order_number} успешно создан!")
            return order_number

    except Exception as e:
        logging.error(f"❌ Error creating order: {e}")
        import traceback
        traceback.print_exc()
        return None


async def get_order(order_number: str) -> Optional[Dict]:
    """Получение информации о заказе"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
                                  SELECT *
                                  FROM orders
                                  WHERE order_number = ?
                                  """, (order_number,))
        order = await cursor.fetchone()

        if not order:
            return None

        order_dict = dict(order)

        # Получение позиций заказа
        cursor = await db.execute("""
                                  SELECT *
                                  FROM order_items
                                  WHERE order_id = ?
                                  """, (order_dict['id'],))
        order_dict['items'] = [dict(row) for row in await cursor.fetchall()]

        return order_dict


async def get_all_orders() -> List[Dict]:
    """Получение всех заказов"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT o.*, u.username, u.first_name 
            FROM orders o 
            JOIN users u ON o.user_id = u.user_id 
            ORDER BY o.created_at DESC
        """)
        orders = []
        for row in await cursor.fetchall():
            order = dict(row)
            # Получение позиций
            cursor_items = await db.execute("""
                SELECT * FROM order_items WHERE order_id = ?
            """, (order['id'],))
            order['items'] = [dict(item) for item in await cursor_items.fetchall()]
            orders.append(order)
        return orders


async def update_order_status(order_number: str, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
                         UPDATE orders
                         SET status = ?
                         WHERE order_number = ?
                         """, (status, order_number))
        await db.commit()

async def get_all_admin_ids() -> List[int]:
    """Получение всех ID администраторов"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE is_admin = 1")
        results = await cursor.fetchall()
        return [row[0] for row in results]


async def delete_order(order_number: str) -> bool:
    """Полное удаление заказа и его позиций"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Получаем ID заказа
            cursor = await db.execute(
                "SELECT id FROM orders WHERE order_number = ?",
                (order_number,)
            )
            result = await cursor.fetchone()

            if not result:
                print(f"❌ Заказ {order_number} не найден в БД")
                return False

            order_id = result[0]
            print(f"🗑️ Удаляем заказ ID={order_id}, номер={order_number}")

            # Удаляем позиции заказа
            await db.execute(
                "DELETE FROM order_items WHERE order_id = ?",
                (order_id,)
            )
            print(f"🗑️ Удалены позиции заказа {order_id}")

            # Удаляем сам заказ
            await db.execute(
                "DELETE FROM orders WHERE id = ?",
                (order_id,)
            )
            print(f"🗑️ Удален заказ {order_id}")

            await db.commit()
            return True

    except Exception as e:
        print(f"❌ Ошибка при удалении заказа: {e}")
        import traceback
        traceback.print_exc()
        return False


async def create_welcome_bonus(user_id: int, discount_percent: int = 10):
    """Создание приветственной скидки для нового пользователя"""
    # Проверяем, есть ли уже активные бонусы
    existing_bonus = await get_active_bonus(user_id)
    if existing_bonus:
        return False  # Бонус уже есть

    # Добавляем новый бонус
    await add_bonus(user_id, discount_percent)
    return True

async def set_bonus_usage(user_id: int, use_bonus: bool):
    """Установка флага использования бонуса для текущего заказа"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO user_settings (user_id, use_bonus) 
            VALUES (?, ?)
        """, (user_id, 1 if use_bonus else 0))
        await db.commit()


async def get_bonus_usage(user_id: int) -> bool:
    """Получение флага использования бонуса"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT use_bonus FROM user_settings WHERE user_id = ?
        """, (user_id,))
        result = await cursor.fetchone()
        return result[0] == 1 if result else True  # По умолчанию True


async def get_maintenance_mode() -> bool:
    """Получение статуса режима техработ"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Проверяем, существует ли таблица settings
            await db.execute("""
                             CREATE TABLE IF NOT EXISTS settings
                             (
                                 key
                                 TEXT
                                 PRIMARY
                                 KEY,
                                 value
                                 TEXT
                             )
                             """)
            await db.commit()

            cursor = await db.execute(
                "SELECT value FROM settings WHERE key = 'maintenance_mode'"
            )
            result = await cursor.fetchone()
            return result[0] == '1' if result else False
    except Exception as e:
        logging.error(f"❌ Ошибка получения статуса техработ: {e}")
        return False


async def set_maintenance_mode(enabled: bool) -> bool:
    """Установка режима техработ"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Создаем таблицу если не существует
            await db.execute("""
                             CREATE TABLE IF NOT EXISTS settings
                             (
                                 key
                                 TEXT
                                 PRIMARY
                                 KEY,
                                 value
                                 TEXT
                             )
                             """)

            await db.execute("""
                INSERT OR REPLACE INTO settings (key, value) 
                VALUES ('maintenance_mode', ?)
            """, ('1' if enabled else '0'))
            await db.commit()

            logging.info(f"🔧 Режим техработ: {'включен' if enabled else 'выключен'}")
            return True
    except Exception as e:
        logging.error(f"❌ Ошибка установки режима техработ: {e}")
        return False