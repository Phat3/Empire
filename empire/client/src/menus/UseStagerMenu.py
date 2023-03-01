import logging
import time
import os
import textwrap

import pyperclip
from prompt_toolkit.completion import Completion

from empire.client.src.EmpireCliConfig import empire_config
from empire.client.src.EmpireCliState import state
from empire.client.src.menus.UseMenu import UseMenu
from empire.client.src.utils.autocomplete_util import (
    filtered_search_list,
    position_util,
)
from empire.client.src.utils.cli_util import command, register_cli_commands
from empire.client.src.utils.data_util import get_random_string

log = logging.getLogger(__name__)


@register_cli_commands
class UseStagerMenu(UseMenu):
    def __init__(self):
        super().__init__(
            display_name="usestager", selected="", record=None, record_options=None
        )

    def autocomplete(self):
        return self._cmd_registry + super().autocomplete()

    def get_completions(self, document, complete_event, cmd_line, word_before_cursor):
        if cmd_line[0] == "usestager" and position_util(
            cmd_line, 2, word_before_cursor
        ):
            for stager in filtered_search_list(
                word_before_cursor, state.stagers.keys()
            ):
                yield Completion(stager, start_position=-len(word_before_cursor))

        yield from super().get_completions(
            document, complete_event, cmd_line, word_before_cursor
        )

    def on_enter(self, **kwargs) -> bool:
        if "selected" not in kwargs:
            return False
        else:
            state.get_bypasses()
            self.use(kwargs["selected"])
            self.info()
            self.options()
            return True

    def use(self, module: str) -> None:
        """
        Use the selected stager.

        Usage: use <module>
        """
        if module in state.stagers.keys():  # todo rename module?
            self.selected = module
            self.record = state.stagers[module]
            self.record_options = state.stagers[module]["options"]

            listener_list = []
            for key, value in self.record_options.items():
                values = list(
                    map(
                        lambda x: "\n".join(textwrap.wrap(str(x), width=35)),
                        value.values(),
                    )
                )
                values.reverse()
                temp = [key] + values
                listener_list.append(temp)

    @command
    def execute(self):
        """
        Execute the stager

        Usage: execute
        """
        # todo validation and error handling
        # Hopefully this will force us to provide more info in api errors ;)
        post_body = {}
        temp_record = {}
        for key, value in self.record_options.items():
            post_body[key] = self.record_options[key]["value"]

        temp_record["options"] = post_body
        temp_record["name"] = get_random_string(10)
        temp_record["template"] = self.record["id"]

        response = state.create_stager(temp_record)
        time.sleep(0.5)

        if "detail" in response:
            log.error(response["detail"])
            return
        elif response.get("options").get("OutFile"):
            stager_data = state.download_stager(response["downloads"][0]["link"])
            if stager_data == "":
                # todo stagers endpoint needs to give modules a way to return errors better.
                #  This says if the output is empty then something must have gone wrong.
                log.error("Stager output empty")
                return
            file_name = response["downloads"][0]["filename"]
            # output_bytes = base64.b64decode(response[self.selected]["Output"])
            directory = f"{state.directory['generated-stagers']}{file_name}"
            with open(directory, "wb") as f:
                f.write(stager_data)
            log.info(f"{file_name} written to {os.path.abspath(directory)}")
        else:
            stager_data = state.download_stager(
                response["downloads"][0]["link"]
            ).decode("UTF-8")
            print(stager_data)
            if empire_config.yaml.get("auto-copy-stagers", {}):
                log.info("Stager copied to clipboard")
                pyperclip.copy(stager_data)

    @command
    def generate(self):
        """
        Generate the stager

        Usage: generate
        """
        self.execute()


use_stager_menu = UseStagerMenu()
