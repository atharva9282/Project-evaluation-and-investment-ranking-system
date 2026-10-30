package org.peirs.model;
import jakarta.persistence.*; import java.math.BigDecimal;
@Entity @Table(name="evaluation_criteria") public class Criterion { @Id @GeneratedValue(strategy=GenerationType.IDENTITY) public Long id; @Column(nullable=false,unique=true) public String name; @Column(nullable=false) public BigDecimal weight; @Column(nullable=false) public boolean enabled=true; public Criterion(){} public Criterion(String n,double w){name=n;weight=BigDecimal.valueOf(w);} }
