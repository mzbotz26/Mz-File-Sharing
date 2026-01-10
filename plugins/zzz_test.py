from bot import Bot

print("ZZZ TEST PLUGIN LOADED")

@Bot.on_message()
async def test_all(client, message):
    print("ZZZ MESSAGE FROM:", message.chat.id)
