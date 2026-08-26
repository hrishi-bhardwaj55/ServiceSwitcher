package com.servicerswitch.engine.api;

import com.servicerswitch.engine.ReconciliationService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/reconcile")
public class ReconcileController {
  private final ReconciliationService service;

  public ReconcileController(ReconciliationService service) {
    this.service = service;
  }

  @PostMapping
  public ReconcileResponse reconcile(@RequestBody ReconcileRequest request) {
    return service.reconcile(request);
  }
}
