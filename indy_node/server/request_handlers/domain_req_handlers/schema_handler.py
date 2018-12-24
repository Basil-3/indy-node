from indy_common.state import domain

from indy_common.roles import Roles

from indy_common.auth import Authoriser

from indy_common.constants import SCHEMA

from indy_common.req_utils import get_write_schema_name, get_write_schema_version
from indy_node.server.request_handlers.read_req_handlers.get_schema_handler import GetSchemaHandler
from plenum.common.constants import DOMAIN_LEDGER_ID
from plenum.common.exceptions import InvalidClientRequest, UnknownIdentifier, UnauthorizedClientRequest

from plenum.common.request import Request
from plenum.common.txn_util import get_type, get_request_data
from plenum.server.database_manager import DatabaseManager
from plenum.server.request_handlers.handler_interfaces.write_request_handler import WriteRequestHandler


class SchemaHandler(WriteRequestHandler):

    def __init__(self, database_manager: DatabaseManager, get_schema_handler: GetSchemaHandler):
        super().__init__(database_manager, SCHEMA, DOMAIN_LEDGER_ID)
        self.get_schema_handler = get_schema_handler

    def static_validation(self, request: Request):
        pass

    def dynamic_validation(self, request: Request):
        # we can not add a Schema with already existent NAME and VERSION
        # sine a Schema needs to be identified by seqNo
        self._validate_type(request)
        identifier, req_id, operation = get_request_data(request)
        schema_name = get_write_schema_name(request)
        schema_version = get_write_schema_version(request)
        schema, _, _, _ = self.get_schema_handler.getSchema(
            author=identifier,
            schemaName=schema_name,
            schemaVersion=schema_version,
            with_proof=False)
        if schema:
            raise InvalidClientRequest(identifier, req_id,
                                       '{} can have one and only one SCHEMA with '
                                       'name {} and version {}'
                                       .format(identifier, schema_name, schema_version))
        try:
            origin_role = self.database_manager.idr_cache.getRole(
                identifier, isCommitted=False) or None
        except BaseException:
            raise UnknownIdentifier(
                identifier,
                req_id)
        r, msg = Authoriser.authorised(typ=SCHEMA,
                                       actorRole=origin_role)
        if not r:
            raise UnauthorizedClientRequest(
                identifier,
                req_id,
                "{} cannot add schema".format(
                    Roles.nameFromValue(origin_role))
            )

    def gen_txn_path(self, txn):
        path = domain.prepare_schema_for_state(txn, path_only=True)
        return path.decode()

    def _update_state_with_single_txn(self, txn, isCommitted=False) -> None:
        assert get_type(txn) == SCHEMA
        path, value_bytes = domain.prepare_schema_for_state(txn)
        self.state.set(path, value_bytes)
