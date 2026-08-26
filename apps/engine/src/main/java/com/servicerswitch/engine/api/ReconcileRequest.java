package com.servicerswitch.engine.api;

import com.servicerswitch.engine.model.MortgageAccount;
import java.time.LocalDate;

public record ReconcileRequest(MortgageAccount account, LocalDate transferDate) {}
