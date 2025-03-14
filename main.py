import asyncio

import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from dataclasses import dataclass
import json
from datetime import datetime, time, timedelta
from aiogram.types import BotCommand
from aiogram.enums import ParseMode
import pytz

moscow_tz = pytz.timezone("Europe/Moscow")
bot = Bot(token="8092647573:AAGnfcFZLW9znsqKQVITLzZs4xYw--efn1E")

dp = Dispatcher()


@dataclass
class WeekInfo:
    day_name: str
    is_even_week: bool


admin = [770833127, 1347201856]

times = {
    "1": "9:30 - 11:00",
    "2": "11:10 - 12:40",
    "3": "13:00 - 14:30",
    "4": "15:00 - 16:30",
    "5": "16:40 - 18:10",
    "6": "18:30 - 20:00"
}

days = {
    "Monday": "Понедельник",
    "Tuesday": "Вторник",
    "Wednesday": "Среда",
    "Thursday": "Четверг",
    "Friday": "Пятница",
    "Saturday": "Суббота",
    "Sunday": "Воскресенье"

}

type_mapping = {
    "lecture": "(Л)",
    "practice": "(Пр)",
    "lab": "(Лр)"
}


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="schedule", description="Получить расписание"),
        BotCommand(command="all", description="Получить все расписание"),
        BotCommand(command="mailing", description="подписаться на рассылку"),
        BotCommand(command="cancel", description="отказаться от рассылки"),
        BotCommand(command="edit", description="редактируем расписание"),
    ]
    await bot.set_my_commands(commands)


def get_week_info() -> WeekInfo:
    url = 'https://api.guap.ru/rasp/v1/get-info'
    headers = {'accept': 'text/plain'}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Ошибка запроса: {response.status_code}")

    data = response.json()

    current_day = data['currentDay'] - 1
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_name = days[current_day]

    is_even_week = data['currentWeek'] % 2 == 0

    return WeekInfo(day_name=day_name, is_even_week=is_even_week)


def print_schedule(next_week: bool):
    info = get_week_info()
    current_date = datetime.now(moscow_tz)
    if next_week:
        current_date = current_date + timedelta(days=1)
    if next_week and info.day_name == "Sunday":
        if info.is_even_week:
            info.is_even_week = False
        else:
            info.is_even_week = True
    if info.is_even_week:
        with open("even.json", "r", encoding="utf-8") as file:
            schedule = json.load(file)
    else:
        with open("notEven.json", "r", encoding="utf-8") as file:
            schedule = json.load(file)
    if next_week:
        day = get_next_day(info.day_name)
    else:
        day = info.day_name
    call_day = days[day]
    if day == "Sunday":
        return "🗓<b>" + call_day + "</b> (" + str(current_date.date().day) + "." + str(current_date.date().month) +")\n\n" + "Пар нет, отдыхаем 🥳"
    if day not in schedule:
        return "День недели не найден."
    day_schedule = schedule[day][0]
    formatted_schedule = ["🗓<b>" + call_day +  "</b> (" + str(current_date.date().day) + "." + str(current_date.date().month) + ")\n"]

    for key, value in day_schedule.items():
        if value["name"] and value["type"]:
            time = times[key]
            name = value["name"]
            description = value["description"]
            if description != "":
                description = "‼️ " + description + "\n"
            type_ = type_mapping.get(value["type"], "")
            formatted_schedule.append(f"{key}. {name} {type_}  {time}\n{description}")

    if len(formatted_schedule) == 1:
        formatted_schedule.append("Пар нет, отдыхаем 🥳")

    return "\n".join(formatted_schedule)


def format_week_schedule(schedule: dict, week_title: str):
    formatted_schedule = [f"{week_title} \n"]

    for day, pairs in schedule.items():
        call_day = days[day]
        formatted_schedule.append(f"🗓<b>{call_day}</b>\n")
        day_schedule = pairs[0]

        has_pairs = False

        for pair_number, pair_info in day_schedule.items():
            if pair_info["name"] and pair_info["type"]:
                time = times[pair_number]
                name = pair_info["name"]
                description = pair_info["description"]
                if description != "":
                    description = "‼️ " + description + "\n"
                type_ = type_mapping.get(pair_info["type"], "")
                formatted_schedule.append(f"{pair_number}. {name} {type_}  {time}\n{description}")
                has_pairs = True

        if not has_pairs:
            formatted_schedule.append("Пар нет, отдыхаем 🥳\n")

    return "\n".join(formatted_schedule)


def print_even_week_schedule():
    with open("even.json", "r", encoding="utf-8") as file:
        even_schedule = json.load(file)
    return format_week_schedule(even_schedule, "🔵Чётная неделя")


def print_not_even_week_schedule():
    with open("notEven.json", "r", encoding="utf-8") as file:
        not_even_schedule = json.load(file)
    return format_week_schedule(not_even_schedule, "🔴Нечётная неделя")


def save_user_id(user_id: int):
    user_ids = load_ids("users.txt")
    if user_id not in user_ids:
        with open("users.txt", "a") as file:
            file.write(f"{user_id}\n")


def save_chat_id(chat_id: int):
    chat_ids = load_ids("chats.txt")
    if chat_id not in chat_ids:
        with open("chats.txt", "a") as file:
            file.write(f"{chat_id}\n")


def remove_user_id(user_id: int):
    user_ids = load_ids("users.txt")
    if user_id in user_ids:
        user_ids.remove(user_id)
        with open("users.txt", "w") as file:
            for id_ in user_ids:
                file.write(f"{id_}\n")


def remove_chat_id(chat_id: int):
    chat_ids = load_ids("chats.txt")
    if chat_id in chat_ids:
        chat_ids.remove(chat_id)
        with open("chats.txt", "w") as file:
            for id_ in chat_ids:
                file.write(f"{id_}\n")


def load_ids(filename: str):
    try:
        with open(filename, "r") as file:
            return [int(line.strip()) for line in file.readlines()]
    except FileNotFoundError:
        return []


def get_next_day(current_day: str) -> str:
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    current_index = days.index(current_day)
    next_index = (current_index + 1) % len(days)
    return days[next_index]


async def send_current_scheduled_messages():
    while True:
        now = datetime.now(moscow_tz).time()
        target_time = time(16, 26)

        if now.hour == target_time.hour and now.minute == target_time.minute:
            user_ids = load_ids("users.txt")
            for user_id in user_ids:
                try:
                    await bot.send_message(user_id, "Расписание на сегодня: \n" + print_schedule(False),
                                           parse_mode=ParseMode.HTML)
                    await bot.send_message(user_id, print_schedule("Расписание на завтра: \n" + print_schedule(True)),
                                           parse_mode=ParseMode.HTML)
                except Exception as e:
                    print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

            chat_ids = load_ids("chats.txt")
            for chat_id in chat_ids:
                try:
                    await bot.send_message(chat_id, print_schedule("Расписание на сегодня: \n" + print_schedule(False)),
                                           parse_mode=ParseMode.HTML)
                    await bot.send_message(chat_id, print_schedule("Расписание на завтра: \n" + print_schedule(True)),
                                           parse_mode=ParseMode.HTML)
                except Exception as e:
                    print(f"Не удалось отправить сообщение в чат {chat_id}: {e}")

        await asyncio.sleep(60)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Я присылаю расписание каждый день")


@dp.message(Command("mailing"))
async def cmd_mailing(message: types.Message):
    chat_id = message.chat.id
    if message.chat.type in ["group", "supergroup", "channel"]:
        save_chat_id(chat_id)
    user_id = message.from_user.id
    save_user_id(user_id)
    await message.answer("Теперь каждый день сюда буду присылать расписание!")


@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message):
    chat_id = message.chat.id
    if message.chat.type in ["group", "supergroup", "channel"]:
        remove_chat_id(chat_id)
    user_id = message.from_user.id
    remove_user_id(user_id)
    await message.answer("Отменил рассылку!")


@dp.message(Command("schedule"))
async def cmd_schedule(message: types.Message):
    await message.answer("Расписание на сегодня: \n" + print_schedule(False), parse_mode=ParseMode.HTML)
    await message.answer("Расписание на завтра: \n" + print_schedule(True), parse_mode=ParseMode.HTML)


@dp.message(Command("all"))
async def all_schedule(message: types.Message):
    if get_week_info().is_even_week:
        await message.answer(print_even_week_schedule(), parse_mode=ParseMode.HTML)
        await message.answer(print_not_even_week_schedule(), parse_mode=ParseMode.HTML)
    else:
        await message.answer(print_not_even_week_schedule(), parse_mode=ParseMode.HTML)
        await message.answer(print_even_week_schedule(), parse_mode=ParseMode.HTML)


@dp.message(Command("edit"))
async def edit_schedule(message: types.Message):
    user_id = message.from_user.id
    if message.chat.type in ["group", "supergroup", "channel"]:
        await message.answer("Нельзя в группе☠️")
    elif user_id not in admin:
        await message.answer("Нет доступа❌")
    elif user_id in admin:
        await message.answer("Изменяем!")


@dp.message()
async def handle_messages(message: types.Message):
    chat_id = message.chat.id
    if message.chat.type in ["group", "supergroup", "channel"]:
        save_chat_id(chat_id)


async def main():
    asyncio.create_task(send_current_scheduled_messages())
    await set_bot_commands(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    print("Starting...")
    asyncio.run(main())
