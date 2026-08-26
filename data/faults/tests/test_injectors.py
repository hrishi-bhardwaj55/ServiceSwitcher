"""Round-trip tests for every single-fault injector."""

from collections.abc import Callable

import pytest
from app.schemas import MortgageAccount

from data.faults.common import FaultInjection
from data.faults.duplicate_tax import inject as inject_duplicate_tax
from data.faults.escrow_balance import inject as inject_escrow_balance
from data.faults.oracle import evaluate
from data.faults.property_tax import inject as inject_property_tax
from data.faults.shortage import inject as inject_shortage
from data.faults.unexplained_payment import inject as inject_unexplained_payment
from data.generator.generate import generate_accounts
from data.generator.validate import validate_account

Injector = Callable[[MortgageAccount, int], FaultInjection]
INJECTORS: tuple[Injector, ...] = (
    inject_escrow_balance,
    inject_property_tax,
    inject_shortage,
    inject_duplicate_tax,
    inject_unexplained_payment,
)


@pytest.mark.parametrize("injector_index", range(len(INJECTORS)))
def test_each_injector_round_trips_exact_impact(injector_index: int) -> None:
    source_accounts = generate_accounts(count=200, seed=20250825)
    injector = INJECTORS[injector_index]

    for variant in range(40):
        source = source_accounts[injector_index * 40 + variant]
        source_json = source.model_dump_json()
        result = injector(source, variant)
        observed = evaluate(result.account)

        assert source.model_dump_json() == source_json
        assert len(observed) == 1
        assert observed[0].finding_type == result.finding_type
        assert observed[0].impact_total == result.impact_total
        assert observed[0].monthly_impact == result.monthly_impact
        assert validate_account(result.account)
