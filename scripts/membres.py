#! /usr/bin/env python
# -*- encoding: utf-8 -*-


import sys
reload(sys)
sys.setdefaultencoding('utf8')

import os
import argparse
import logging
import datetime
import erppeek
import csv
import base64

from cfg_secret_configuration import odoo_configuration_user_prod as user_config

###############################################################################
# Odoo Connection
###############################################################################
def init_openerp(url, login, password, database):
    openerp = erppeek.Client(url)
    uid = openerp.login(login, password=password, database=database)
    user = openerp.ResUsers.browse(uid)
    tz = user.tz
    return openerp, uid, tz

openerp, uid, tz = init_openerp(
    user_config['url'],
    user_config['login'],
    user_config['password'],
    user_config['database'])


###############################################################################
# Configuration
###############################################################################

###############################################################################
# Script
###############################################################################

exported_fields = [
        "num",
        "name",
        "surname",
        "barcode",
        "sex",
        "birthdate",
        "email",
        "cooperative_state"]

def add_member_to_list(member, member_list):
    (name, surname) = member.name.split(',', 1)
    member_list.append(
            {
            "num": member.barcode_base,
            "name": name,
            "surname": surname.strip(),
            "barcode": member.barcode,
            "sex": member.sex,
            "birthdate": member.birthdate,
            "email": member.email,
            "cooperative_state": member.cooperative_state,
            }
    )

def save_csv(file_name, fields, data):
    csvfile = open(file_name, 'wb')
    csvwriter = csv.DictWriter(csvfile, quoting=csv.QUOTE_ALL,
        fieldnames=fields)
    csvwriter.writeheader()
    for elt in data:
        csvwriter.writerow(elt)
    csvfile.close()

def main():
    # configure arguments parser
    parser = argparse.ArgumentParser(
            description='Export des membres')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('output_dir', metavar='OUTPUT_DIR',
            help='the output directory')
    args = parser.parse_args()

    # configure logger
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    today = datetime.date.today().isoformat()
    nb_member = 0
    exported_members = []
    try:
        # Create output dirs
        if not os.path.isdir(args.output_dir):
            os.makedirs(args.output_dir)
        # List members
        members = openerp.ResPartner.browse([('is_worker_member', '=', 'true')])
        for member in members:
            if ',' not in member.name:
                continue
            add_member_to_list(member, exported_members)
            logging.info("Data extracted for [%s]", member.name)
            nb_member = nb_member+1

        # Create output csv
        save_csv("%s/membres.csv" % (args.output_dir), exported_fields,
                exported_members)
        print "Total: %d members exported from Odoo" % (nb_member)


    except Exception as e:
        logging.exception(e)

if __name__ == "__main__":
    main()
