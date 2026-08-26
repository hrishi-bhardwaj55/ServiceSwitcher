package com.servicerswitch.engine.findings;

import static com.servicerswitch.engine.TestAccounts.TRANSFER_DATE;
import static com.servicerswitch.engine.TestAccounts.account;
import static com.servicerswitch.engine.TestAccounts.amount;
import static com.servicerswitch.engine.TestAccounts.analysis;
import static com.servicerswitch.engine.TestAccounts.baseAccount;
import static com.servicerswitch.engine.TestAccounts.context;
import static com.servicerswitch.engine.TestAccounts.decomposition;
import static org.assertj.core.api.Assertions.assertThat;

import com.servicerswitch.engine.model.EscrowTransaction;
import com.servicerswitch.engine.model.MortgageAccount;
import com.servicerswitch.engine.model.TransactionType;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.Test;

class DetectorBoundaryTest {
    private final EscrowBalanceMismatchDetector balanceDetector = new EscrowBalanceMismatchDetector();
    private final PropertyTaxProjectionMismatchDetector taxDetector = new PropertyTaxProjectionMismatchDetector();
    private final EscrowShortageCalculationErrorDetector shortageDetector = new EscrowShortageCalculationErrorDetector();
    private final DuplicateTaxDisbursementDetector duplicateDetector = new DuplicateTaxDisbursementDetector();
    private final UnexplainedPaymentIncreaseDetector paymentDetector = new UnexplainedPaymentIncreaseDetector();

    @Test
    void balanceDetectorFiresAboveTolerance() {
        MortgageAccount account = account(
                analysis(LocalDate.of(2024, 5, 31), amount("1000.00"), amount("6000.00"), amount("400.00")),
                analysis(TRANSFER_DATE, amount("1001.01"), amount("6000.00"), amount("400.00")),
                List.of());
        assertThat(balanceDetector.detect(context(account))).isPresent();
    }

    @Test
    void balanceDetectorIgnoresNearMissAndBoundary() {
        assertBalanceDoesNotFire("1000.99");
        assertBalanceDoesNotFire("1001.00");
    }

    private void assertBalanceDoesNotFire(String newBalance) {
        MortgageAccount account = account(
                analysis(LocalDate.of(2024, 5, 31), amount("1000.00"), amount("6000.00"), amount("400.00")),
                analysis(TRANSFER_DATE, amount(newBalance), amount("6000.00"), amount("400.00")),
                List.of());
        assertThat(balanceDetector.detect(context(account))).isEmpty();
    }

    @Test
    void taxDetectorFiresAboveGreaterOfTolerance() {
        assertThat(taxDetector.detect(context(withProjectedTax("6060.01")))).isPresent();
    }

    @Test
    void taxDetectorIgnoresNearMissAndBoundary() {
        assertThat(taxDetector.detect(context(withProjectedTax("6059.99")))).isEmpty();
        assertThat(taxDetector.detect(context(withProjectedTax("6060.00")))).isEmpty();
    }

    private MortgageAccount withProjectedTax(String projection) {
        return account(
                analysis(LocalDate.of(2024, 5, 31), amount("1200.00"), amount("6000.00"), amount("400.00")),
                analysis(TRANSFER_DATE, amount("1200.00"), amount(projection), amount("400.00")),
                List.of());
    }

    @Test
    void shortageDetectorFiresAboveTolerance() {
        assertThat(shortageDetector.detect(context(withStatedShortage("410.01"), amount("400.00"), decomposition(amount("0.00"), amount("10.00"), FindingType.EXPLAINED)))).isPresent();
    }

    @Test
    void shortageDetectorIgnoresNearMissAndBoundary() {
        assertShortageDoesNotFire("409.99");
        assertShortageDoesNotFire("410.00");
    }

    private void assertShortageDoesNotFire(String shortage) {
        assertThat(shortageDetector.detect(context(
                        withStatedShortage(shortage),
                        amount("400.00"),
                        decomposition(amount("0.00"), amount("10.00"), FindingType.EXPLAINED))))
                .isEmpty();
    }

    private MortgageAccount withStatedShortage(String shortage) {
        return account(
                analysis(LocalDate.of(2024, 5, 31), amount("1200.00"), amount("6000.00"), amount("400.00")),
                analysis(TRANSFER_DATE, amount("1200.00"), amount("6000.00"), amount(shortage)),
                List.of());
    }

    @Test
    void duplicateDetectorFiresForSimilarPaymentWithinWindow() {
        assertThat(duplicateDetector.detect(context(withTaxPayments(30, "1000.00")))).isPresent();
    }

    @Test
    void duplicateDetectorIgnoresNearMissOutsideWindow() {
        assertThat(duplicateDetector.detect(context(withTaxPayments(46, "1000.00")))).isEmpty();
    }

    @Test
    void duplicateDetectorIncludesExactDayAndAmountBoundary() {
        assertThat(duplicateDetector.detect(context(withTaxPayments(45, "980.00")))).isPresent();
    }

    private MortgageAccount withTaxPayments(int dayDifference, String secondAmount) {
        LocalDate firstDate = LocalDate.of(2025, 1, 1);
        return account(
                analysis(LocalDate.of(2024, 5, 31), amount("1200.00"), amount("6000.00"), amount("400.00")),
                analysis(TRANSFER_DATE, amount("1200.00"), amount("6000.00"), amount("400.00")),
                List.of(
                        new EscrowTransaction(firstDate, TransactionType.TAX_DISBURSEMENT, amount("-1000.00"), "County", amount("0.00")),
                        new EscrowTransaction(firstDate.plusDays(dayDifference), TransactionType.TAX_DISBURSEMENT, amount("-" + secondAmount), "County", amount("0.00"))));
    }

    @Test
    void paymentDetectorFiresAboveTolerance() {
        assertThat(paymentDetector.detect(context(
                        baseAccount(),
                        amount("400.00"),
                        decomposition(amount("10.01"), amount("10.00"), FindingType.UNEXPLAINED_PAYMENT_INCREASE))))
                .get()
                .extracting(Finding::findingType)
                .isEqualTo(FindingType.UNEXPLAINED_PAYMENT_INCREASE);
    }

    @Test
    void paymentDetectorEmitsExplainedForNearMissAndBoundary() {
        assertExplained("9.99");
        assertExplained("10.00");
    }

    private void assertExplained(String residual) {
        Finding finding = paymentDetector.detect(context(
                        baseAccount(),
                        amount("400.00"),
                        decomposition(amount(residual), amount("10.00"), FindingType.EXPLAINED)))
                .orElseThrow();
        assertThat(finding.findingType()).isEqualTo(FindingType.EXPLAINED);
    }
}
