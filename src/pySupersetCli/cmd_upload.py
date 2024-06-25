"""Upload a JSON file to a Superset instance."""

# BSD 3-Clause License
#
# Copyright (c) 2024, NewTec GmbH
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICU5LAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

################################################################################
# Imports
################################################################################

import os
import argparse
import logging
import pandas as pd
from pySupersetCli.ret import Ret
from pySupersetCli.superset import Superset

################################################################################
# Variables
################################################################################

LOG: logging.Logger = logging.getLogger(__name__)
_CMD_NAME = "upload"
_TEMP_FILE_NAME = "./temp.csv"

################################################################################
# Classes
################################################################################

################################################################################
# Functions
################################################################################


def register(subparser) -> dict:
    """ Register subparser commands.

    Args:
        subparser (obj):   the command subparser provided via __main__.py

    Returns:
        obj:    the command parser of this module
    """
    cmd_dict: dict = {
        "name": _CMD_NAME,
        "handler": _execute
    }

    sub_parser_search: argparse.ArgumentParser = \
        subparser.add_parser(_CMD_NAME,
                             help="Upload a JSON file to a Superset instance.")

    required_subarguments = sub_parser_search.add_argument_group(
        'required arguments')

    required_subarguments.add_argument('-d',
                                       '--database',
                                       type=int,
                                       metavar='<database_pk>',
                                       required=True,
                                       help="The primary key of the database to " +
                                       "upload the JSON file to.")

    required_subarguments.add_argument('-t',
                                       '--table',
                                       type=str,
                                       metavar='<table_name>',
                                       required=True,
                                       help="The name of the table to upload the JSON file to.")

    required_subarguments.add_argument('-f',
                                       '--file',
                                       type=str,
                                       metavar='<input_file>',
                                       required=True,
                                       help="The JSON input file to upload.")

    return cmd_dict


def _execute(args, superset_client: Superset) -> Ret:
    """ This function serves as entry point for the command.
        It will be stored as callback for this module's subparser command.

    Args: 
        args (obj): The command line arguments.
        superset_client (obj): The Superset client object.

    Returns:
        Ret: The status of the command execution.
    """

    return_status = Ret.OK

    if ("" != args.table) and ("" != args.file) and (None is not superset_client):
        try:
            with open(args.file, mode="r", encoding="UTF-8") as json_file:
                # Input is a list of dictionaries.
                data_frame = pd.read_json(json_file, orient='records')

            # pylint: disable=no-member
            data_frame.to_csv(_TEMP_FILE_NAME, encoding="UTF-8", index=False)

            with open(_TEMP_FILE_NAME, 'rb') as csv_file:
                upload_file = {'file': csv_file}
                upload_body = {'already_exists': 'append',
                               'table_name': args.table}

                # Upload the CSV file to the specified table
                ret_code, ret_data = \
                    superset_client.request("POST",
                                            f"/database/{args.database}/csv_upload/",
                                            data=upload_body,
                                            files=upload_file)

            if ret_data.get("message") == "OK":
                LOG.info("Upload successful.")
            else:
                LOG.error("Upload failed: [%d] %s",
                          ret_code, ret_data.get("message"))
                return_status = Ret.ERROR_UPLOAD_FAILED

            if os.path.exists(_TEMP_FILE_NAME):
                os.remove(_TEMP_FILE_NAME)

        except Exception as e:  # pylint: disable=broad-except
            LOG.error("%s", e)
            return_status = Ret.ERROR_INVALID_ARGUMENTS

    return return_status

################################################################################
# Main
################################################################################
