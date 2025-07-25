from odoo import models, api, fields, _
import requests
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Main order fields
    x_studio_order_number_1 = fields.Char(string="Order Number")
    x_studio_customer_code = fields.Char(string="Customer Code")
    x_studio_warehouse = fields.Char(string="Warehouse")
    x_studio_reference = fields.Char(string="Reference")
    x_studio_order_date = fields.Datetime(string="Order Date")
    x_studio_job_reference = fields.Char(string="Job Reference")
    x_studio_customer_reference = fields.Char(string="Customer Reference")
    x_studio_carrier_code = fields.Char(string="Carrier Code")
    x_studio_trackingnumber = fields.Char(string="Tracking Number")
    x_studio_extra_charges = fields.Float(string="Extra Charges")
    x_studio_instructions = fields.Text(string="Instructions")
    x_studio_date_wanted = fields.Datetime(string="Date Wanted")

    # Receiver details
    x_studio_code = fields.Char(string="Receiver Code")
    x_studio_name = fields.Char(string="Receiver Name")
    x_studio_address = fields.Text(string="Receiver Address")
    x_studio_suburb = fields.Char(string="Receiver Suburb")
    x_studio_state_code = fields.Char(string="Receiver State Code")
    x_studio_post_code = fields.Char(string="Receiver Post Code")
    x_studio_country_code = fields.Char(string="Receiver Country Code", default='AU')
    x_studio_telephone = fields.Char(string="Receiver Telephone")
    x_studio_email = fields.Char(string="Receiver Email")

    # Tracking Number Fields
    x_studio_customer_reference_1=fields.Char(string="Customer Reference For Tracking Number")
    x_studio_customer_code_1=fields.Char(string="Customer Code For Tracking Number")
    x_studio_tracking_number_view=fields.Char(string="Tracking Number View")

    @api.model_create_multi
    def create(self, vals_list):
        print("DEBUG: Entering create method with vals_list:", vals_list)

        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                print("DEBUG: Generating sequence for new order")
                seq_date = fields.Datetime.context_timestamp(
                    self, fields.Datetime.to_datetime(vals.get('date_order'))
                ) if 'date_order' in vals else None
                vals['name'] = self.env['ir.sequence'].with_company(vals.get('company_id')).next_by_code(
                    'sale.order', sequence_date=seq_date) or _("New")
                print("DEBUG: Generated order name:", vals['name'])

        print("DEBUG: Calling super().create()")
        sale_orders = super().create(vals_list)
        print("DEBUG: Created sale orders:", sale_orders)

        # Send API for each order
        for order in sale_orders:
            try:
                print(f"DEBUG: Processing order {order.name} for API call")

                def format_datetime(dt):
                    return dt.strftime("%Y-%m-%dT%H:%M:%S") if dt else None

                # Prepare order lines
                order_lines = []
                for line in order.order_line:
                    line_data = {
                        "ProductCode": line.x_studio_product_code or line.product_id.default_code or line.name,
                        "UOM": line.x_studio_uom or line.product_uom.name,
                        "QtyOrdered": float(line.x_studio_qty_ordered or line.product_uom_qty)
                    }
                    print(f"DEBUG: Order line {line.id} data:", line_data)
                    order_lines.append(line_data)

                payload = {
                    "OrderNumber": order.x_studio_order_number_1,
                    "CustomerCode": order.x_studio_customer_code ,
                    "Warehouse": order.x_studio_warehouse ,
                    "Reference": order.x_studio_reference ,
                    "OrderDate": format_datetime(order.x_studio_order_date),
                    "DateWanted": format_datetime(order.x_studio_date_wanted),
                    "JobReference": order.x_studio_job_reference ,
                    "CustomerReference": order.x_studio_customer_reference,
                    "CarrierCode": order.x_studio_carrier_code or "",
                    "TrackingNumber": order.x_studio_trackingnumber or "",
                    "ExtraCharges": float(order.x_studio_extra_charges) if order.x_studio_extra_charges else 0.0,
                    "Receiver": {
                        "Code": order.x_studio_code,
                        "Name": order.x_studio_name,
                        "Address": order.x_studio_address,
                        "Suburb": order.x_studio_suburb,
                        "StateCode": order.x_studio_state_code or "VIC",
                        "PostCode": order.x_studio_post_code,
                        "CountryCode": order.x_studio_country_code or "AU",
                        "Telephone": order.x_studio_telephone,
                        "Email": order.x_studio_email
                    },
                    "Instructions": order.x_studio_instructions,
                    "Notes": None,
                    "CustomerOrderLines": order_lines
                }

                print(f"DEBUG: Final payload for order {order.name}:", payload)

                url = "https://push-api-uat.bdladvantage.com/v2/PartnerOrder"
                headers = {
                    "Authorization": "ask for the api key",
                    "Content-Type": "application/json"
                }

                print(f"DEBUG: Sending API request for order {order.name}")
                response = requests.post(url, json=payload, headers=headers)
                print(f"DEBUG: API response - Status: {response.status_code}, Body: {response.text}")

                _logger.info("API POST to Dynamics - Status: %s - Body: %s", response.status_code, response.text)

                if response.status_code != 200:
                    _logger.warning("API call failed for order %s", order.name)
                    order.message_post(body=f"API Response: {response.status_code} - {response.text}")
                    print(f"DEBUG: API call failed for order {order.name}")

            except Exception as e:
                _logger.exception("Exception during API call for order %s: %s", order.name, str(e))
                print(f"DEBUG: Exception processing order {order.name}: {str(e)}")

        print("DEBUG: Returning created sale orders")
        return sale_orders



# Get Tracking Number Method
    def get_tracking_number(self):
        for order in self:
            payload = {
                "CustomerReference": order.x_studio_customer_reference_1,
                "CustomerCode": order.x_studio_customer_code_1,
            }

            url = f"https://push-api-uat.bdladvantage.com/v2/trackingNumbers/{order.x_studio_customer_code_1}/{order.x_studio_customer_reference_1}"

            headers = {
                "Authorization": "bad06b49-4883-4d9d-919c-8e1a1c59dd16",
                "Content-Type": "application/json"
            }

            # Debug prints
            print("Sending request to:", url)
            print("Headers:", headers)

            try:
                response = requests.get(url, headers=headers, timeout=10)
                print("HTTP Status Code:", response.status_code)
                response.raise_for_status()

                data = response.json()
                print("Response JSON:", data)

                # Extract list of tracking codes
                tracking_codes = data.get("trackingCodes", [])
                print("Tracking Codes:", tracking_codes)

                if tracking_codes:
                    # Save all tracking codes as comma-separated string
                    order.x_studio_trackingnumber = ", ".join(tracking_codes)
                    order.x_studio_trackingnumber = order.x_studio_tracking_number_view
                else:
                    order.x_studio_trackingnumber = "No Tracking Codes Returned"

            except requests.exceptions.RequestException as e:
                error_message = f"API Error: {str(e)}"
                print(error_message)
                order.x_studio_trackingnumber = error_message
        return {'type': 'ir.actions.client', 'tag': 'reload'}