# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    # BDynamic Integration Fields
    x_studio_send_to_bdynamic = fields.Boolean(string='Send to BDynamic Logistics', default=True)
    x_studio_order_type = fields.Char(string='Order Type', default='PP')
    x_studio_warehouse = fields.Char(string='Warehouse', default='PWH8')
    x_studio_principal_code = fields.Char(string='Principal Code', default='61414')
    x_studio_reference = fields.Char(string='Reference')
    x_studio_job_reference = fields.Char(string='Job Reference')
    x_studio_customer_reference = fields.Char(string='Customer Reference')
    x_studio_order_date = fields.Datetime(string='Order Date', default=fields.Datetime.now)
    x_studio_date_wanted = fields.Datetime(string='Date Wanted', default=fields.Datetime.now)
    x_studio_eta_date = fields.Datetime(string='ETA Date', default=fields.Datetime.now)
    x_studio_instructions = fields.Text(string='Instructions')
    x_studio_order_notes = fields.Text(string='Order Notes')
    x_studio_delivery_docket_number = fields.Char(string='Delivery Docket Number')
    x_studio_supplier_invoice_number = fields.Char(string='Supplier Invoice Number')
    x_studio_stock_method = fields.Char(string='Stock Method')

    # Stock Order Line Fields
    x_studio_line_number = fields.Integer(string='Line Number', default=1)
    x_studio_product_code = fields.Char(string='Product Code')
    x_studio_item_desc = fields.Text(string='Item Description')
    x_studio_item_short_desc = fields.Char(string='Item Short Description')
    x_studio_item_width = fields.Float(string='Item Width', default=2.0)
    x_studio_item_length = fields.Float(string='Item Length', default=2.0)
    x_studio_item_height = fields.Float(string='Item Height', default=2.0)
    x_studio_item_vol = fields.Float(string='Item Volume', default=1.5)
    x_studio_item_weight = fields.Float(string='Item Weight', default=1.6)
    x_studio_item_barcode = fields.Char(string='Item Barcode')
    x_studio_item_type = fields.Char(string='Item Type', default='Cartoon')
    x_studio_item_group = fields.Char(string='Item Group', default='A')
    x_studio_uom_stock = fields.Char(string='UOM', default='UNIT')
    x_studio_notes_stock = fields.Text(string='Notes')
    x_studio_qty_received = fields.Float(string='Qty Received', default=1.0)
    x_studio_qty_ordered_stock = fields.Float(string='Qty Ordered', default=0.0)
    x_studio_gtin_barcode = fields.Char(string='GTIN Barcode')

    x_studio_principal_code_1 = fields.Char(string='Principal Code', default='61414')
    x_studio_customer_ref = fields.Char(string='Customer Reference')
    x_studio_sku = fields.Char(string='SKU Result', readonly=True)
    x_studio_qty = fields.Float(string='Quantity Result', readonly=True)

    def _format_datetime_for_api(self, datetime_field):
        """Format datetime field for API"""
        if datetime_field:
            formatted_datetime = datetime_field.strftime('%Y-%m-%dT%H:%M:%S')
            print(f"DEBUG: Formatted datetime {datetime_field} to {formatted_datetime}")
            return formatted_datetime
        default_datetime = fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        print(f"DEBUG: Using default datetime: {default_datetime}")
        return default_datetime

    def _prepare_bdynamic_payload(self):
        """Prepare JSON payload for BDynamic API"""
        print("DEBUG: Starting to prepare BDynamic payload...")

        payload = {
            "orderType": self.x_studio_order_type or "PP",
            "warehouse": self.x_studio_warehouse or "PWH8",
            "principalCode": self.x_studio_principal_code or "61414",
            "reference": self.x_studio_reference or "",
            "jobReference": self.x_studio_job_reference or "",
            "customerReference": self.x_studio_customer_reference or "",
            "orderDate": self._format_datetime_for_api(self.x_studio_order_date),
            "dateWanted": self._format_datetime_for_api(self.x_studio_date_wanted),
            "etaDate": self._format_datetime_for_api(self.x_studio_eta_date),
            "instructions": self.x_studio_instructions or "",
            "orderNotes": self.x_studio_order_notes or "",
            "deliveryDocketNumber": self.x_studio_delivery_docket_number or "",
            "supplierInvoiceNumber": self.x_studio_supplier_invoice_number or "",
            "stockMethod": self.x_studio_stock_method or "N",
            "stockOrderLines": [
                {
                    "lineNumber": self.x_studio_line_number or 1,
                    "productCode": self.x_studio_product_code or "",
                    "ItemDesc": self.x_studio_item_desc or "",
                    "ItemShortdesc": self.x_studio_item_short_desc or "",
                    "ItemWidth": self.x_studio_item_width or 2.0,
                    "ItemLength": self.x_studio_item_length or 2.0,
                    "ItemHeight": self.x_studio_item_height or 2.0,
                    "ItemVol": self.x_studio_item_vol or 1.5,
                    "ItemWeight": self.x_studio_item_weight or 1.6,
                    "ItemBarcode": self.x_studio_item_barcode or "",
                    "ItemType": self.x_studio_item_type or "Cartoon",
                    "ItemGroup": self.x_studio_item_group or "A",
                    "uom": self.x_studio_uom_stock or "UNIT",
                    "notes": self.x_studio_notes_stock or "",
                    "qtyReceived": self.x_studio_qty_received or 1.0,
                    "qtyOrdered": self.x_studio_qty_ordered_stock or 0.0,
                    "gtinBarcode": self.x_studio_gtin_barcode or ""
                }
            ]
        }

        print("DEBUG: Prepared payload:")
        print(json.dumps(payload, indent=2, default=str))
        return payload

    def _send_to_bdynamic_api(self, payload):
        """Send data to BDynamic API"""
        print("DEBUG: Starting API request to BDynamic...")
        print(f"DEBUG: API URL: https://push-api-uat.bdladvantage.com/v2/StockOrder")

        try:
            api_url = "https://push-api-uat.bdladvantage.com/v2/StockOrder"

            headers = {
                "Authorization": "bad06b49-4883-4d9d-919c-8e1a1c59dd16",
                "Content-Type": "application/json"
            }

            print("DEBUG: Request headers:")
            print(json.dumps(headers, indent=2))

            print("DEBUG: Sending POST request...")
            response = requests.post(
                api_url,
                headers=headers,
                json=payload
            )

            print(f"DEBUG: Response status code: {response.status_code}")
            print(f"DEBUG: Response headers: {dict(response.headers)}")
            print(f"DEBUG: Response content: {response.text}")

            if response.status_code == 200:
                print("DEBUG: API request successful!")
                _logger.info(f"Successfully sent data to BDynamic API. Response: {response.text}")
                return True, response.json() if response.content else {}
            else:
                error_msg = f"BDynamic API error - Status: {response.status_code}, Response: {response.text}"
                print(f"DEBUG: API request failed - {error_msg}")
                _logger.error(error_msg)
                return False, error_msg

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to connect to BDynamic API: {str(e)}"
            print(f"DEBUG: Request exception - {error_msg}")
            _logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error sending to BDynamic API: {str(e)}"
            print(f"DEBUG: Unexpected exception - {error_msg}")
            _logger.error(error_msg)
            return False, error_msg

    def action_send_to_bdynamic(self):
        """Manual action to send existing quant to BDynamic API"""
        print("DEBUG: action_send_to_bdynamic called")
        print(f"DEBUG: x_studio_send_to_bdynamic flag: {self.x_studio_send_to_bdynamic}")

        if not self.x_studio_send_to_bdynamic:
            print("DEBUG: Send to BDynamic is disabled, raising UserError")
            raise UserError(_("Please enable 'Send to BDynamic Logistics' first."))

        print("DEBUG: Preparing payload...")
        payload = self._prepare_bdynamic_payload()

        print("DEBUG: Sending to API...")
        success, response = self._send_to_bdynamic_api(payload)

        print(f"DEBUG: API call result - Success: {success}, Response: {response}")

        if success:
            print("DEBUG: Returning success notification")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Data sent to BDynamic API successfully.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            print(f"DEBUG: Raising UserError due to API failure: {response}")
            raise UserError(_(f"Failed to send data to BDynamic API: {response}"))

    def _get_bdynamic_stock_order(self, principal_code, customer_reference):
        """Core API communication method"""
        print(f"DEBUG: Starting API request with Principal: {principal_code}, Customer Ref: {customer_reference}")

        try:
            api_url = f"https://push-api-uat.bdladvantage.com/v2/StockOrder/{principal_code}/{customer_reference}"
            headers = {
                "Authorization": "bad06b49-4883-4d9d-919c-8e1a1c59dd16",
                "Content-Type": "application/json"
            }

            print(f"DEBUG: API URL: {api_url}")
            print(f"DEBUG: Request Headers: {headers}")

            _logger.info(f"Fetching stock order: {api_url}")
            print("DEBUG: Making GET request to BDynamic API...")

            response = requests.get(api_url, headers=headers)
            print(f"DEBUG: Received response - Status Code: {response.status_code}")

            response.raise_for_status()
            print("DEBUG: API request successful (2XX status code)")

            json_response = response.json()
            print(f"DEBUG: API Response (raw): {json.dumps(json_response, indent=2)}")

            return True, json_response

        except requests.exceptions.RequestException as e:
            error_msg = f"API Error: {str(e)}"
            print(f"DEBUG: Request Exception - {error_msg}")
            _logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"DEBUG: Unexpected Error - {error_msg}")
            _logger.error(error_msg)
            return False, error_msg

    def action_get_bdynamic_stock_order(self):
        """Main execution method"""
        print("DEBUG: Starting action_get_bdynamic_stock_order")
        self.ensure_one()

        # Validate input
        print(f"DEBUG: Checking customer reference - Current value: {self.x_studio_customer_ref}")
        if not self.x_studio_customer_ref:
            print("DEBUG: Validation failed - Missing customer reference")
            raise UserError(_("Customer Reference is required"))

        # Get parameters
        principal_code = self.x_studio_principal_code_1 or "61414"
        customer_ref = self.x_studio_customer_ref or ""
        print(f"DEBUG: Using parameters - Principal: {principal_code}, Customer Ref: {customer_ref}")

        # API call
        print("DEBUG: Initiating API call...")
        success, response = self._get_bdynamic_stock_order(principal_code, customer_ref)

        if not success:
            print(f"DEBUG: API call failed - {response}")
            raise UserError(_(f"API Error: {response}"))

        # Parse response
        print("DEBUG: Parsing API response...")
        try:
            print("DEBUG: Attempting to extract first order line")
            first_order = response['productStockOrders'][0]
            print(f"DEBUG: First order details: {first_order.get('orderNo', 'N/A')}")

            order_lines = first_order['lines']
            print(f"DEBUG: Found {len(order_lines)} order lines")

            first_line = order_lines[0]
            print(f"DEBUG: First line details - SKU: {first_line.get('sku')}, Qty: {first_line.get('qty')}")

            update_vals = {
                'x_studio_sku': first_line.get('sku', 'N/A'),
                'x_studio_qty': first_line.get('qty', 0)
            }
            print(f"DEBUG: Updating fields with values: {update_vals}")

            self.write(update_vals)
            print("DEBUG: Field update successful")

        except (KeyError, IndexError) as e:
            error_msg = f"DEBUG: Response parsing failed - {str(e)}"
            print(error_msg)
            print(f"DEBUG: Full response structure: {json.dumps(response, indent=2)}")
            raise UserError(_("Invalid API response format"))

        print("DEBUG: action_get_bdynamic_stock_order completed successfully")