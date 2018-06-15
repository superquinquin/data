#! /usr/bin/env python
# -*- encoding: utf-8 -*-


import sys
reload(sys)
sys.setdefaultencoding('utf8')

import os
import argparse
import logging
import erppeek
import csv
import unidecode
import datetime
import dateutil.relativedelta as reldelta

from cfg_secret_configuration import odoo_configuration_user_prod as odoo_conf

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
    odoo_conf['url'],
    odoo_conf['login'],
    odoo_conf['password'],
    odoo_conf['database'])


###############################################################################
# Configuration
###############################################################################

###############################################################################
# Script
###############################################################################

def norm(string):
    return unidecode.unidecode(unicode(str(string), 'utf-8'))

output_fields = [
    'Nom',
    'Date creation',
    'Type',
    'Code Barre',
    'Cat Interne',
    'Unite de mesure',
    'Categorie Fiscale',
    'Coefficient 9',
    'Prix de base',
    'Prix Theorique TTC',
    'Prix de vente']

def main():
    # configure arguments parser
    parser = argparse.ArgumentParser(
            description='Dump CSV de tous les articles créés depuis un mois')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-d', '--dest', help='Liste de mail destination')
    parser.add_argument('output_dir', metavar='OUTPUT_DIR',
            help='the output directory')
    args = parser.parse_args()

    # configure logger
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    today = datetime.date.today()

    # open csv file
    csv_file_name = "%s/articles_recents_%s.csv" % (args.output_dir,
            today.isoformat())
    csvfile = open(csv_file_name, 'wb')
    csvwriter = csv.DictWriter(csvfile, delimiter=';', quoting=csv.QUOTE_ALL,
            fieldnames=output_fields)
    csvwriter.writeheader()

    last_month = (today - reldelta.relativedelta(months=+1)).isoformat()

    for article in openerp.ProductTemplate.browse(
            [("sale_ok", "=", "true"),
                ("create_date", ">", last_month)
                ]):
        csvwriter.writerow({
            output_fields[0]: norm(article.name),
            output_fields[1]: norm(article.create_date),
            output_fields[2]: norm(article.type),
            output_fields[3]: norm(article.barcode),
            output_fields[4]: norm(article.categ_id.name),
            output_fields[5]: norm(article.uom_id.name),
            output_fields[6]: norm(article.fiscal_classification_id.name),
            output_fields[7]: norm(article.coeff9_id),
            output_fields[8]: norm(article.base_price),
            output_fields[9]: norm(article.theoritical_price),
            output_fields[10]: norm(article.list_price)})

    csvfile.close()

    email_cmd = "sendemail \
            -f admin@data.superquinquin.fr \
            -t %s \
            -u \"[SQQ] Rapport mensuel articles\" \
            -m \"Liste des articles crees sur Odoo ce dernier mois\" \
            -a %s" % (args.dest, csv_file_name)
    os.system(email_cmd)

if __name__ == "__main__":
    main()
