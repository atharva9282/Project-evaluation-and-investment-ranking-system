package org.peirs.service;
import org.junit.jupiter.api.Test; import static org.junit.jupiter.api.Assertions.*;
class FinancialEngineTest { @Test void calculatesPositiveNpvAndRoi(){var result=FinancialEngine.calculate(1000,500,100,4,.08);assertTrue((double)result.get("npv")>0);assertEquals(60.0,result.get("roi"));assertEquals(2.5,result.get("paybackYears"));} @Test void rejectsInvalidDiscountRate(){assertThrows(IllegalArgumentException.class,()->FinancialEngine.calculate(1000,100,20,5,1.5));} }
