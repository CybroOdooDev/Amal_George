from odoo import http, fields, _
from odoo.http import request
import logging
import werkzeug.utils

_logger = logging.getLogger(__name__)


class PharmaVendorPortal(http.Controller):

    def _ensure_db(self):
        """
        Switches the active database to the one specified in the `db` query
        parameter, if it differs from the current session database.
        Returns True if a redirect was issued (caller must return the redirect),
        False otherwise.
        """
        db_param = request.params.get('db', '').strip()
        if not db_param:
            return False

        from odoo.http import db_filter
        # Validate the db param is a real, reachable database
        if not db_filter([db_param]):
            _logger.warning('pharma portal: requested db %r not in db_filter', db_param)
            return False

        if request.session.db == db_param:
            # Already on the right database — nothing to do
            return False

        # Switch the session to the requested database and redirect so that
        # Odoo's normal database-aware dispatcher picks up the new session.
        request.session.db = db_param
        return True

    def _check_access(self, qualification_id, access_token):
        """Validates the qualification record and token securely."""
        if not qualification_id or not access_token:
            return None
        if 'pharma.vendor.qualification' not in request.env:
            return None
        # Must use sudo() to bypass record rules for the public user, relying strictly on the token
        qual_sudo = request.env['pharma.vendor.qualification'].sudo().browse(qualification_id)
        if not qual_sudo.exists() or qual_sudo.access_token != access_token:
            return None
        return qual_sudo

    @http.route(['/pharma/vendor/questionnaire/<int:qualification_id>'], type='http', auth="public", website=True)
    def vendor_questionnaire(self, qualification_id, access_token=None, **kwargs):
        if self._ensure_db():
            return request.redirect(request.httprequest.url)

        qual_sudo = self._check_access(qualification_id, access_token)
        if not qual_sudo:
            _logger.warning(
                'pharma portal: 403 for qualification_id=%s, token=%s, session_db=%s',
                qualification_id, access_token, request.session.db,
            )
            return request.render('http_routing.403')

        values = {
            'qualification': qual_sudo,
            'access_token': access_token,
        }
        return request.render('pharmaceutical_erp.portal_vendor_questionnaire', values)

    @http.route(['/pharma/vendor/questionnaire/<int:qualification_id>/submit'], type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def vendor_questionnaire_submit(self, qualification_id, access_token=None, **post):
        qual_sudo = self._check_access(qualification_id, access_token)
        if not qual_sudo:
            return request.render('http_routing.403')

        # Process the submitted responses
        for response in qual_sudo.response_ids:
            answer_type = response.question_id.answer_type
            if answer_type == 'yes_no':
                val = post.get(f'answer_yes_no_{response.id}')
                if val in ['True', 'False', 'yes', 'no']:
                    response.answer_yes_no = 'yes' if val in ('True', 'yes') else 'no'
            elif answer_type == 'text':
                val = post.get(f'answer_text_{response.id}')
                if val is not None:
                    response.answer_text = val
            elif answer_type == 'number':
                val = post.get(f'answer_number_{response.id}')
                if val:
                    try:
                        response.answer_number = float(val)
                    except ValueError:
                        pass # Ignore invalid numbers

        # Set submission date
        qual_sudo.submission_date = fields.Datetime.now()

        # Log action in chatter
        qual_sudo.message_post(body=_("Vendor has submitted the qualification questionnaire via the portal."))
        
        # Advance the workflow status if it was in 'questionnaire_sent'
        if qual_sudo.status == 'questionnaire_sent':
            qual_sudo.status = 'documents_received'

        # Send Notification to QA
        if qual_sudo.create_uid and qual_sudo.create_uid.email:
            template = request.env.ref('pharmaceutical_erp.email_template_vendor_submission_notification', raise_if_not_found=False)
            if template:
                template.sudo().send_mail(qual_sudo.id, force_send=True)

        return request.render('pharmaceutical_erp.portal_vendor_questionnaire_success', {
            'qualification': qual_sudo
        })
