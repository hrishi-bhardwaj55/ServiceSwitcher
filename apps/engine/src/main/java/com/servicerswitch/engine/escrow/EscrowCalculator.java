package com.servicerswitch.engine.escrow;

import static com.servicerswitch.engine.money.Money.TWELVE;
import static com.servicerswitch.engine.money.Money.ZERO;
import static com.servicerswitch.engine.money.Money.cents;
import static com.servicerswitch.engine.money.Money.divide;

import com.servicerswitch.engine.model.EscrowAnalysis;
import com.servicerswitch.engine.model.MortgageAccount;
import com.servicerswitch.engine.model.TaxBill;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

public final class EscrowCalculator {
  private record Charge(int month, BigDecimal amount) {}

  public EscrowComputation compute(
      MortgageAccount account, EscrowAnalysis analysis, int projectionYear) {
    BigDecimal monthlyEscrow =
        divide(analysis.projectedAnnualTax().add(analysis.projectedAnnualInsurance()), TWELVE);
    List<Charge> charges = projectedCharges(account, analysis, projectionYear);
    BigDecimal balance = cents(analysis.currentBalance());
    BigDecimal lowBalance = balance;
    LocalDate firstMonth = analysis.analysisDate().withDayOfMonth(1);
    if (analysis.analysisDate().getDayOfMonth() > 1) {
      firstMonth = firstMonth.plusMonths(1);
    }
    for (int offset = 0; offset < 12; offset++) {
      int month = firstMonth.plusMonths(offset).getMonthValue();
      balance = cents(balance.add(monthlyEscrow));
      for (Charge charge : charges) {
        if (charge.month() == month) {
          balance = cents(balance.subtract(charge.amount()));
        }
      }
      if (balance.compareTo(lowBalance) < 0) {
        lowBalance = balance;
      }
    }
    BigDecimal cushion =
        divide(
            analysis.projectedAnnualTax().add(analysis.projectedAnnualInsurance()),
            new BigDecimal("6"));
    BigDecimal shortage = cushion.subtract(lowBalance).max(ZERO);
    shortage = cents(shortage);
    return new EscrowComputation(
        monthlyEscrow, lowBalance, cushion, shortage, divide(shortage, TWELVE));
  }

  private List<Charge> projectedCharges(
      MortgageAccount account, EscrowAnalysis analysis, int projectionYear) {
    List<Charge> actualTaxCharges = new ArrayList<>();
    for (TaxBill bill : account.taxBills()) {
      if (bill.taxYear() != projectionYear) {
        continue;
      }
      List<BigDecimal> installments = split(bill.annualAmount(), bill.dueDates().size());
      for (int index = 0; index < bill.dueDates().size(); index++) {
        actualTaxCharges.add(
            new Charge(bill.dueDates().get(index).getMonthValue(), installments.get(index)));
      }
    }
    BigDecimal actualTaxTotal =
        actualTaxCharges.stream().map(Charge::amount).reduce(ZERO, BigDecimal::add);
    List<Charge> projected = new ArrayList<>();
    BigDecimal allocated = ZERO;
    for (int index = 0; index < actualTaxCharges.size(); index++) {
      Charge actual = actualTaxCharges.get(index);
      BigDecimal amount;
      if (index == actualTaxCharges.size() - 1) {
        amount = cents(analysis.projectedAnnualTax().subtract(allocated));
      } else {
        amount =
            cents(
                analysis
                    .projectedAnnualTax()
                    .multiply(actual.amount())
                    .divide(actualTaxTotal, 12, java.math.RoundingMode.HALF_UP));
        allocated = cents(allocated.add(amount));
      }
      projected.add(new Charge(actual.month(), amount));
    }
    account.insurancePolicies().stream()
        .filter(policy -> policy.renewalDate().getYear() == projectionYear)
        .findFirst()
        .ifPresent(
            policy ->
                projected.add(
                    new Charge(
                        policy.renewalDate().getMonthValue(),
                        analysis.projectedAnnualInsurance())));
    return projected;
  }

  private List<BigDecimal> split(BigDecimal total, int parts) {
    long centsTotal = cents(total).movePointRight(2).longValueExact();
    long base = centsTotal / parts;
    long remainder = centsTotal % parts;
    List<BigDecimal> installments = new ArrayList<>();
    for (int index = 0; index < parts; index++) {
      installments.add(BigDecimal.valueOf(base + (index < remainder ? 1 : 0), 2));
    }
    return installments;
  }
}
