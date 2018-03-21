#! /usr/bin/env python
# -*- encoding: utf-8 -*-


import sys
reload(sys)
sys.setdefaultencoding('utf8')

import argparse
import logging
import erppeek
import decimal as d
import json
import datetime

from cfg_secret_configuration import odoo_configuration_user_prod as odoo_configuration_user

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
    odoo_configuration_user['url'],
    odoo_configuration_user['login'],
    odoo_configuration_user['password'],
    odoo_configuration_user['database'])


###############################################################################
# Configuration
###############################################################################

###############################################################################
# Script
###############################################################################

def dec_round(x):
    # all results are rounded to 2 places after coma
    TWOPLACES = d.Decimal(10) ** -2
    return float(d.Decimal(str(x)).quantize(TWOPLACES, rounding=d.ROUND_HALF_UP))

def compute_line(line):
    # Get TVA type (5.5, 20, etc.)
    if len(line.tax_ids) < 1:
        type_tva = 0.0
    else:
        type_tva = line.tax_ids[0].amount
    # Calculate price including discounts
    corrected_price = line.price_unit * (1 - line.discount / 100)
    line_ttc = dec_round(corrected_price * line.qty)
    line_tva = dec_round(line_ttc - (line_ttc / (1 + type_tva / 100)))
    logging.debug("Line [%s] %f * %f = %f including %f (TVA=%f%%)",
            line.product_id.name, corrected_price, line.qty, line_ttc, line_tva, type_tva)
    return (type_tva, line_ttc, line_tva)

def normalize_payment_mean(mean):
    if mean.startswith("CB"):
        return "CB"
    else:
        return mean

def main():
    # configure arguments parser
    parser = argparse.ArgumentParser(description='Créé un rapport des ventes')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('output_dir', metavar='OUTPUT_DIR', help='the output directory')
    parser.add_argument('report_date', metavar='REPORT_DATE', nargs='?',
            help='the date to create the report for (YYYY-MM-DD)')
    args = parser.parse_args()

    # configure logger
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # If no date provided, use today as default
    if args.report_date is None:
        args.report_date = datetime.date.today().isoformat()

    logging.info("Creating report for date [%s] in directory [%s]",
            args.report_date, args.output_dir)

    total_sale_ttc = {}
    total_sale = 0.00
    total_payment_mean = {}
    total_payment = 0.00
    total_articles = 0
    total_tickets = 0
    output_data = {
            "date": args.report_date,
            "sale_by_tva": [],
            "payment_by_mean": []
            }

    select = "create_date =ilike %s%%" % (args.report_date)
    for order in openerp.PosOrder.browse([select]):
        total_tickets += 1
        order_payment = 0.00
        for stmt in order.statement_ids:
            order_payment += stmt.amount
            mean = normalize_payment_mean(stmt.journal_id.code)
            if mean not in total_payment_mean.keys():
                total_payment_mean[mean] = 0.00
            total_payment_mean[mean] += stmt.amount

        order_sale_ttc = 0.00
        for line in order.lines:
            total_articles += 1
            (type_tva, line_ttc, line_tva) = compute_line(line)
            order_sale_ttc += line_ttc
            if type_tva not in total_sale_ttc.keys():
                total_sale_ttc[type_tva] = {"ttc": 0.00, "tva": 0.00}
            total_sale_ttc[type_tva]["ttc"] += line_ttc
            total_sale_ttc[type_tva]["tva"] += line_tva
        logging.debug("Order [%s] sale=%f, payment=%f",
                order.name, order_sale_ttc, order_payment)

    for type_tva in total_sale_ttc.keys():
        ttc = total_sale_ttc[type_tva]["ttc"]
        tva = total_sale_ttc[type_tva]["tva"]
        logging.info("TVA %s%% - %f + %f = %f", type_tva, ttc-tva, tva, ttc)
        tva_sale = {
                "label": "TVA %s%%" % (type_tva),
                "ht": str(ttc-tva),
                "tva": str(tva),
                "ttc": str(ttc)
                }
        output_data["sale_by_tva"].append(tva_sale)
        total_sale += ttc

    for mean in total_payment_mean.keys():
        amount = total_payment_mean[mean]
        logging.info("Total paiement %s : %f", mean, amount)
        payment = {
                "mean": mean,
                "amount": str(amount)
                }
        output_data["payment_by_mean"].append(payment)
        total_payment += amount

    logging.info("Total : %f", total_sale)
    output_data["total_sale"] = str(total_sale)
    logging.info("Total paiement : %f", total_payment)
    output_data["total_payment"] = str(total_payment)
    output_data["total_articles"] = str(total_articles)
    output_data["total_tickets"] = str(total_tickets)

    # Create output json
    data_file = open("%s/sales_%s.json" % (args.output_dir, args.report_date), 'w')
    json.dump(output_data, data_file, indent=4)
    data_file.close()

if __name__ == "__main__":
    main()
