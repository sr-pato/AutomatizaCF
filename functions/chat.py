from database.utils import load_db
from database.types import GeneralUser
from wrappers import wrappers_map
from json import load as load_jsonfile
from functions.state import StateProcess
from telebot import TeleBot
from json import dumps

class ChatBot:
    def __init__(self, messages_infos:dict, platform:str, enviroment_vars:dict, telegram_bot:TeleBot) -> None:
        self.env_vars = enviroment_vars
        self.messages_infos = messages_infos
        self.platform = wrappers_map.get(platform)
        self.retrieve_invoker(platform)
        self.messages_tree = load_jsonfile(open(self.env_vars.get("MESSAGES_TREE_PATH"), "r", encoding="utf-8"))
        self.telegram_bot = telegram_bot
        self.execute_state()

    def retrieve_invoker(self, platform:str):
        self.invoker = GeneralUser()
        self.invoker.user_id = self.messages_infos['messages'][0]['from']
        self.invoker.phone_number_id = self.messages_infos['metadata']['phone_number_id']
        
        conn = load_db(self.env_vars.get("DB_PATH"))
        invoker_infos = conn.execute("select first_name, last_name, state, telefone, email from general_users where (user_id = ? or phone_number_id = ?) and platform = ?", (self.invoker.user_id, self.invoker.phone_number_id, platform)).fetchone()
        if invoker_infos:
            self.invoker.first_name, self.invoker.last_name, self.invoker.state, self.invoker.telefone, self.invoker.email = invoker_infos
            print(dumps(self.messages_infos, indent=4), end="\n\n\n\n")
            self.invoker.first_name = self.invoker.first_name if self.invoker.first_name == self.messages_infos.get("contacts", [{"profile": {'name': ''}}])[0].get("profile")['name'] else self.messages_infos['contacts'][0]["profile"]['name']
        else:
            user_name = self.messages_infos["contacts"][0]['profile']['name'] if self.messages_infos.get("contacts") is not None else "Usuário"
            print(user_name)
            conn.execute("insert or replace into general_users (first_name, last_name, state, telefone, user_id, phone_number_id, platform) values (?, ?, ?, ?, ?, ?, ?)", (user_name, '-', 'init', self.invoker.user_id, self.invoker.user_id, self.invoker.phone_number_id, platform))
            conn.commit()
            conn.close()
            return self.retrieve_invoker(platform)
        self.invoker.platform = platform
        conn.execute("update general_users set first_name = ? where (user_id = ? or phone_number_id = ?) and platform = ?", (self.invoker.first_name, self.invoker.user_id, self.invoker.phone_number_id, self.invoker.platform))
        conn.commit()
        conn.close()
    
    def execute_state(self):
        state_obj = StateProcess(self.invoker, self.messages_tree, self.env_vars, load_db(self.env_vars.get("DB_PATH")), self.platform, self.messages_infos, self.telegram_bot)