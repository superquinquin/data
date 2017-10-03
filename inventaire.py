#! /usr/bin/env python
# -*- encoding: utf-8 -*-


import sys
reload(sys)
sys.setdefaultencoding('utf8')

import datetime
import time
import erppeek

from datetime import date

from cfg_secret_configuration import odoo_configuration_user


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

## On parcourt les fournisseurs  
#partners = openerp.ResPartner.browse([('supplier','=','true'),('name','like','Thir')])
partners = openerp.ResPartner.browse([('supplier','=','true')])

## Nb de partner 
print "Found %d suppliers" % len(partners)

file = open("output/inventaire.html","w") 

header='<html  xmlns="http://www.w3.org/1999/xhtml" xml:lang="fr" lang="fr" dir="ltr" <head> <meta http-equiv="Content-Type" content="text/html; charset=utf-8" /> <style> .text { font-family: times, monospace; font-size:8pt;  } </style></head><body class="text"> '

file.write( "%s" %(header))

## On parcourt les partners 
for partner in partners:
	file.write( "<li><a href='%s.html'>%s</a> %s </li>" % (partner.id,partner.id,partner.name,) )

	filepart = open("output/%s.html" %(partner.id),"w") 
	filepart.write( "%s <a href='inventaire.html'>Retour liste</a> " %(header))

	print 	partner.id,":",partner.name 
	filepart.write( "<h1>%s</h1> <ul>" % (partner.name))

	products = openerp.ProductProduct.browse([('main_seller_id','=',partner.name),('sale_ok','=','true')])
	#products = openerp.ProductProduct.browse([])
	print ">>>> Number of product found: ", len(products)
	for product in products : 
		#DEBUG lister tous les champs de l'objet
		#l=dir(product) 
		#print l


		filepart.write( "<li>%s %s" %(format(product.qty_available),product.name) )
		print "{:4.0f}".format(product.qty_available) ," ",product.name, "(",product.id,") "
	filepart.close 

file.close

