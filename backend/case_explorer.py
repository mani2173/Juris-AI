"""
Legal Case Explorer - Argument Graph Generator
Converts case analysis data into interactive argument visualization structure
"""

import uuid
import json

def generate_case_explorer_graph(case_analysis):
    """
    Convert comprehensive case analysis into interactive argument graph.
    
    Returns:
    {
        "parties": [...],
        "nodes": [...],
        "edges": [...],
        "inspector_details": {...}
    }
    """
    
    if not case_analysis:
        return None
    
    try:
        parties = []
        nodes = []
        edges = []
        inspector_details = {}
        node_id_counter = 0
        
        # Extract parties
        party_a = case_analysis.get("party_a", {})
        party_b = case_analysis.get("party_b", {})
        metadata = case_analysis.get("case_metadata", {})
        
        party_a_name = party_a.get("party_name", "Party A")
        party_b_name = party_b.get("party_name", "Party B")
        
        parties = [
            {
                "id": "party_a",
                "name": party_a_name,
                "type": "petitioner",
                "risk_level": party_a.get("overall_risk_level", "Medium")
            },
            {
                "id": "party_b",
                "name": party_b_name,
                "type": "respondent",
                "risk_level": party_b.get("overall_risk_level", "Medium")
            }
        ]
        
        # ===== PARTY A ARGUMENTS =====
        
        # Party A - Core Legal Position (support node)
        node_id = f"node_{node_id_counter}"
        node_id_counter += 1
        nodes.append({
            "id": node_id,
            "type": "support",
            "party": "party_a",
            "title": "Core Legal Position",
            "label": party_a.get("core_legal_position", "Legal position")[:80],
            "strength_score": 65
        })
        position_node_a = node_id
        inspector_details[node_id] = {
            "title": "Core Legal Position",
            "explanation": party_a.get("core_legal_position", ""),
            "related_legal_provision": "Primary legal basis",
            "evidence_linked": party_a.get("supporting_arguments", []),
            "strength_score": 65,
            "risk_impact_level": party_a.get("overall_risk_level", "Medium")
        }
        
        # Party A - Supporting Arguments
        supporting_args_a = party_a.get("supporting_arguments", [])
        for idx, arg in enumerate(supporting_args_a[:3]):  # Limit to 3
            node_id = f"node_{node_id_counter}"
            node_id_counter += 1
            nodes.append({
                "id": node_id,
                "type": "support",
                "party": "party_a",
                "title": f"Supporting Argument {idx+1}",
                "label": str(arg)[:60],
                "strength_score": 70
            })
            inspector_details[node_id] = {
                "title": f"Supporting Argument {idx+1}",
                "explanation": str(arg),
                "related_legal_provision": metadata.get("statutes_referenced", ["N/A"])[0] if metadata.get("statutes_referenced") else "N/A",
                "evidence_linked": metadata.get("evidence_submitted", []),
                "strength_score": 70,
                "risk_impact_level": "Low"
            }
            # Edge: support argument -> core position
            edges.append({
                "source": node_id,
                "target": position_node_a,
                "relationship": "support_of"
            })
        
        # Party A - Weaknesses (counter nodes)
        weaknesses_a = party_a.get("weaknesses", [])
        for idx, weakness in enumerate(weaknesses_a[:2]):  # Limit to 2
            node_id = f"node_{node_id_counter}"
            node_id_counter += 1
            nodes.append({
                "id": node_id,
                "type": "counter",
                "party": "party_a",
                "title": f"Weakness {idx+1}",
                "label": str(weakness)[:60],
                "strength_score": 45
            })
            inspector_details[node_id] = {
                "title": f"Weakness in Party A's Case",
                "explanation": str(weakness),
                "related_legal_provision": "Procedural requirement",
                "evidence_linked": ["Gap in evidence"],
                "strength_score": 45,
                "risk_impact_level": "High"
            }
            # Edge: weakness -> contradicts position
            edges.append({
                "source": node_id,
                "target": position_node_a,
                "relationship": "counter_to"
            })
        
        # Party A - Legal Basis (evidence node)
        node_id = f"node_{node_id_counter}"
        node_id_counter += 1
        statutes = metadata.get("statutes_referenced", ["Applicable Law"])
        statute_text = statutes[0] if statutes else "Applicable Law"
        nodes.append({
            "id": node_id,
            "type": "legal_basis",
            "party": "party_a",
            "title": "Legal Basis",
            "label": statute_text[:50],
            "strength_score": 75
        })
        legal_basis_a = node_id
        inspector_details[node_id] = {
            "title": "Legal Basis / Statutes",
            "explanation": f"Applicable statutes and legal provisions: {statute_text}",
            "related_legal_provision": statute_text,
            "evidence_linked": metadata.get("statutes_referenced", []),
            "strength_score": 75,
            "risk_impact_level": "Low"
        }
        edges.append({
            "source": legal_basis_a,
            "target": position_node_a,
            "relationship": "based_on"
        })
        
        # Party A - Evidence (evidence node)
        node_id = f"node_{node_id_counter}"
        node_id_counter += 1
        evidence_text = ", ".join(metadata.get("evidence_submitted", ["Documentary evidence"])[:2])
        nodes.append({
            "id": node_id,
            "type": "evidence",
            "party": "party_a",
            "title": "Supporting Evidence",
            "label": evidence_text[:50],
            "strength_score": int(party_a.get("evidence_strength", "Medium") == "High" and 80 or 60)
        })
        evidence_node_a = node_id
        inspector_details[node_id] = {
            "title": "Supporting Evidence",
            "explanation": f"Evidence strength: {party_a.get('evidence_strength', 'Medium')}",
            "related_legal_provision": statute_text,
            "evidence_linked": metadata.get("evidence_submitted", []),
            "strength_score": int(party_a.get("evidence_strength", "Medium") == "High" and 80 or 60),
            "risk_impact_level": "Low"
        }
        edges.append({
            "source": evidence_node_a,
            "target": position_node_a,
            "relationship": "supported_by_evidence"
        })
        
        # ===== PARTY B ARGUMENTS =====
        
        # Party B - Core Legal Position (support node)
        node_id = f"node_{node_id_counter}"
        node_id_counter += 1
        nodes.append({
            "id": node_id,
            "type": "support",
            "party": "party_b",
            "title": "Core Legal Position",
            "label": party_b.get("core_legal_position", "Legal position")[:80],
            "strength_score": 65
        })
        position_node_b = node_id
        inspector_details[node_id] = {
            "title": "Core Legal Position",
            "explanation": party_b.get("core_legal_position", ""),
            "related_legal_provision": "Primary legal defense",
            "evidence_linked": party_b.get("supporting_arguments", []),
            "strength_score": 65,
            "risk_impact_level": party_b.get("overall_risk_level", "Medium")
        }
        
        # Party B - Supporting Arguments
        supporting_args_b = party_b.get("supporting_arguments", [])
        for idx, arg in enumerate(supporting_args_b[:3]):  # Limit to 3
            node_id = f"node_{node_id_counter}"
            node_id_counter += 1
            nodes.append({
                "id": node_id,
                "type": "support",
                "party": "party_b",
                "title": f"Defense Argument {idx+1}",
                "label": str(arg)[:60],
                "strength_score": 70
            })
            inspector_details[node_id] = {
                "title": f"Defense Argument {idx+1}",
                "explanation": str(arg),
                "related_legal_provision": metadata.get("statutes_referenced", ["N/A"])[0] if metadata.get("statutes_referenced") else "N/A",
                "evidence_linked": metadata.get("evidence_submitted", []),
                "strength_score": 70,
                "risk_impact_level": "Low"
            }
            # Edge: defense argument -> core position
            edges.append({
                "source": node_id,
                "target": position_node_b,
                "relationship": "support_of"
            })
        
        # Party B - Weaknesses (counter nodes)
        weaknesses_b = party_b.get("weaknesses", [])
        for idx, weakness in enumerate(weaknesses_b[:2]):  # Limit to 2
            node_id = f"node_{node_id_counter}"
            node_id_counter += 1
            nodes.append({
                "id": node_id,
                "type": "counter",
                "party": "party_b",
                "title": f"Weakness {idx+1}",
                "label": str(weakness)[:60],
                "strength_score": 45
            })
            inspector_details[node_id] = {
                "title": f"Weakness in Party B's Case",
                "explanation": str(weakness),
                "related_legal_provision": "Procedural requirement",
                "evidence_linked": ["Gap in evidence"],
                "strength_score": 45,
                "risk_impact_level": "High"
            }
            # Edge: weakness -> contradicts position
            edges.append({
                "source": node_id,
                "target": position_node_b,
                "relationship": "counter_to"
            })
        
        # Party B - Legal Basis (evidence node)
        node_id = f"node_{node_id_counter}"
        node_id_counter += 1
        nodes.append({
            "id": node_id,
            "type": "legal_basis",
            "party": "party_b",
            "title": "Legal Basis",
            "label": statute_text[:50],
            "strength_score": 75
        })
        legal_basis_b = node_id
        inspector_details[node_id] = {
            "title": "Legal Basis / Statutes",
            "explanation": f"Applicable statutes and legal provisions: {statute_text}",
            "related_legal_provision": statute_text,
            "evidence_linked": metadata.get("statutes_referenced", []),
            "strength_score": 75,
            "risk_impact_level": "Low"
        }
        edges.append({
            "source": legal_basis_b,
            "target": position_node_b,
            "relationship": "based_on"
        })
        
        # Party B - Evidence (evidence node)
        node_id = f"node_{node_id_counter}"
        node_id_counter += 1
        nodes.append({
            "id": node_id,
            "type": "evidence",
            "party": "party_b",
            "title": "Supporting Evidence",
            "label": evidence_text[:50],
            "strength_score": int(party_b.get("evidence_strength", "Medium") == "High" and 80 or 60)
        })
        evidence_node_b = node_id
        inspector_details[node_id] = {
            "title": "Supporting Evidence",
            "explanation": f"Evidence strength: {party_b.get('evidence_strength', 'Medium')}",
            "related_legal_provision": statute_text,
            "evidence_linked": metadata.get("evidence_submitted", []),
            "strength_score": int(party_b.get("evidence_strength", "Medium") == "High" and 80 or 60),
            "risk_impact_level": "Low"
        }
        edges.append({
            "source": evidence_node_b,
            "target": position_node_b,
            "relationship": "supported_by_evidence"
        })
        
        # ===== CROSS-PARTY RELATIONSHIPS =====
        # Add counter relationships between opposing positions
        edges.append({
            "source": position_node_b,
            "target": position_node_a,
            "relationship": "counter_to"
        })
        
        return {
            "parties": parties,
            "nodes": nodes,
            "edges": edges,
            "inspector_details": inspector_details,
            "case_metadata": {
                "title": metadata.get("case_title", "Case"),
                "court": metadata.get("court", "Not specified"),
                "year": metadata.get("year"),
                "legal_issues": metadata.get("legal_issues", [])
            }
        }
    
    except Exception as e:
        print(f"❌ Case Explorer graph generation error: {e}")
        return None
