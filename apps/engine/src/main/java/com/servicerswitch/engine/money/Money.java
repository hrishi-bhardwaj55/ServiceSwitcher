package com.servicerswitch.engine.money;

import java.math.BigDecimal;
import java.math.RoundingMode;

public final class Money {
    public static final BigDecimal ZERO = new BigDecimal("0.00");
    public static final BigDecimal TWELVE = new BigDecimal("12");

    private Money() {}

    public static BigDecimal cents(BigDecimal value) {
        return value.setScale(2, RoundingMode.HALF_UP);
    }

    public static BigDecimal divide(BigDecimal value, BigDecimal divisor) {
        return value.divide(divisor, 2, RoundingMode.HALF_UP);
    }

    public static BigDecimal absoluteDifference(BigDecimal first, BigDecimal second) {
        return cents(first.subtract(second).abs());
    }

    public static BigDecimal maximum(BigDecimal first, BigDecimal second) {
        return first.compareTo(second) >= 0 ? first : second;
    }
}
