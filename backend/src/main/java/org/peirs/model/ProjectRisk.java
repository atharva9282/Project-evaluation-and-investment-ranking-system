package org.peirs.model;
import jakarta.persistence.*;
@Entity @Table(name="project_risks") public class ProjectRisk { @Id @GeneratedValue(strategy=GenerationType.IDENTITY) public Long id; @ManyToOne(optional=false) @JoinColumn(name="project_id") public Project project; @Column(name="risk_type",nullable=false) public String riskType; @Column(nullable=false,columnDefinition="text") public String description; @Column(nullable=false) public int probability; @Column(nullable=false) public int impact; @Column(columnDefinition="text") public String mitigation; }
