package com.servicerswitch.engine.findings;

import java.math.BigDecimal;

public final class Tolerances {
  // Audit comparison around transfer continuity under 12 CFR 1024.17(e).
  public static final BigDecimal ESCROW_BALANCE = new BigDecimal("1.00");
  // Projection comparison around escrow estimates under 12 CFR 1024.17(c).
  public static final BigDecimal TAX_ABSOLUTE = new BigDecimal("25.00");
  public static final BigDecimal TAX_PERCENT = new BigDecimal("0.01");
  // Aggregate-analysis comparison under 12 CFR 1024.17(d).
  public static final BigDecimal SHORTAGE = new BigDecimal("10.00");
  // Duplicate timing guard around timely disbursement under 12 CFR 1024.17(k).
  public static final int DUPLICATE_DAYS = 45;
  public static final BigDecimal DUPLICATE_PERCENT = new BigDecimal("0.02");
  // Payment-change comparison using escrow statement components in 12 CFR 1024.17(g).
  public static final BigDecimal PAYMENT_ABSOLUTE = new BigDecimal("10.00");
  public static final BigDecimal PAYMENT_PERCENT = new BigDecimal("0.02");

  private Tolerances() {}
}
