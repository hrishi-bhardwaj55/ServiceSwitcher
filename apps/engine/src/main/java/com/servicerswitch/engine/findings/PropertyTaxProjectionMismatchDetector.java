package com.servicerswitch.engine.findings;

import static com.servicerswitch.engine.findings.FindingSupport.finding;
import static com.servicerswitch.engine.money.Money.TWELVE;
import static com.servicerswitch.engine.money.Money.absoluteDifference;
import static com.servicerswitch.engine.money.Money.cents;
import static com.servicerswitch.engine.money.Money.divide;
import static com.servicerswitch.engine.money.Money.maximum;

import com.servicerswitch.engine.model.EscrowAnalysis;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

public final class PropertyTaxProjectionMismatchDetector implements FindingDetector {
    @Override
    public Optional<Finding> detect(ReconciliationContext context) {
        EscrowAnalysis analysis = context.account().escrowAnalyses()
                .get(context.account().escrowAnalyses().size() - 1);
        int projectionYear = context.account().taxBills().stream()
                .mapToInt(bill -> bill.taxYear())
                .max()
                .orElseThrow(() -> new IllegalArgumentException("missing tax bill"));
        BigDecimal billed = cents(context.account().taxBills().stream()
                .filter(bill -> bill.taxYear() == projectionYear)
                .map(bill -> bill.annualAmount())
                .reduce(BigDecimal.ZERO, BigDecimal::add));
        BigDecimal difference = absoluteDifference(analysis.projectedAnnualTax(), billed);
        BigDecimal tolerance = maximum(
                Tolerances.TAX_ABSOLUTE, cents(billed.multiply(Tolerances.TAX_PERCENT)));
        if (difference.compareTo(tolerance) <= 0) {
            return Optional.empty();
        }
        return Optional.of(finding(
                FindingType.PROPERTY_TAX_PROJECTION_MISMATCH,
                billed,
                analysis.projectedAnnualTax(),
                difference,
                divide(difference, TWELVE),
                "The escrow tax projection differs from the supplied annual tax bills.",
                List.of(
                        new Evidence("doc_property_tax_bill", 1, "annual_tax", billed),
                        new Evidence("doc_escrow_analysis", 1, "projected_annual_tax", analysis.projectedAnnualTax())),
                "Ask the servicer to update or substantiate the projected property tax."));
    }
}
