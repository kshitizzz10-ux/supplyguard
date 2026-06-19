import pandas as pd

def calculate_delivery_score(on_time_rate, quantity_fulfillment_rate, late_deliveries):
    # on_time_rate is already a percentage (0-100)
    # quantity_fulfillment_rate is already a percentage (0-100)
    # late_deliveries in last 6 months, max we consider is 6
    
    late_penalty = min(late_deliveries * 8, 40)  # each late delivery costs 8 points, max 40
    
    delivery_score = (on_time_rate * 0.5) + (quantity_fulfillment_rate * 0.5) - late_penalty
    delivery_score = max(0, min(100, delivery_score))  # clamp between 0 and 100
    
    return round(delivery_score, 1)


def calculate_quality_score(defect_rate, quality_complaints):
    # defect_rate is a percentage, lower is better
    # quality_complaints count, lower is better
    
    defect_score = max(0, 100 - (defect_rate * 6))  # 0% defect = 100, each % costs 6 points
    complaint_penalty = min(quality_complaints * 5, 40)  # each complaint costs 5 points
    
    quality_score = defect_score - complaint_penalty
    quality_score = max(0, min(100, quality_score))
    
    return round(quality_score, 1)


def calculate_financial_score(gst_q1, gst_q2, gst_q3, gst_q4, advance_requests):
    # count how many quarters GST was filed
    quarters = [gst_q1, gst_q2, gst_q3, gst_q4]
    filed_count = sum(1 for q in quarters if str(q).strip().lower() == 'yes')
    
    gst_score = (filed_count / 4) * 100  # 4/4 filed = 100, 2/4 = 50, etc.
    advance_penalty = min(advance_requests * 10, 40)  # each advance request costs 10 points
    
    financial_score = gst_score - advance_penalty
    financial_score = max(0, min(100, financial_score))
    
    return round(financial_score, 1)


def calculate_communication_score(response_time_hours, last_minute_reschedules):
    # response_time_hours: lower is better, anything above 24 is very bad
    # last_minute_reschedules: lower is better
    
    if response_time_hours <= 2:
        response_score = 100
    elif response_time_hours <= 6:
        response_score = 85
    elif response_time_hours <= 12:
        response_score = 65
    elif response_time_hours <= 24:
        response_score = 40
    else:
        response_score = 15
    
    reschedule_penalty = min(last_minute_reschedules * 12, 50)
    
    communication_score = response_score - reschedule_penalty
    communication_score = max(0, min(100, communication_score))
    
    return round(communication_score, 1)


def calculate_health_score(row, weights=None):
    if weights is None:
        weights = {'delivery': 0.35, 'quality': 0.25, 'financial': 0.25, 'communication': 0.15}
    
    delivery = calculate_delivery_score(
        row['on_time_rate'],
        row['quantity_fulfillment_rate'],
        row['late_deliveries_last_6_months']
    )
    quality = calculate_quality_score(
        row['defect_rate'],
        row['quality_complaints']
    )
    financial = calculate_financial_score(
        row['gst_filed_q1'], row['gst_filed_q2'],
        row['gst_filed_q3'], row['gst_filed_q4'],
        row['advance_payment_requests']
    )
    communication = calculate_communication_score(
        row['response_time_hours'],
        row['last_minute_reschedules']
    )

    total = sum(weights.values())
    final_score = (
        (delivery * (weights['delivery'] / total)) +
        (quality * (weights['quality'] / total)) +
        (financial * (weights['financial'] / total)) +
        (communication * (weights['communication'] / total))
    )

    return {
        'health_score': round(max(0, min(100, final_score)), 1),
        'delivery_score': delivery,
        'quality_score': quality,
        'financial_score': financial,
        'communication_score': communication
    }


def get_status(score):
    if score >= 70:
        return 'Healthy', '🟢'
    elif score >= 40:
        return 'Watch', '🟡'
    else:
        return 'At Risk', '🔴'


def process_suppliers(df, weights=None):
    results = []
    
    for _, row in df.iterrows():
        scores = calculate_health_score(row, weights)
        status, emoji = get_status(scores['health_score'])
        
        results.append({
            'supplier_name': row['supplier_name'],
            'category': row['category'],
            'location': row['location'],
            'health_score': scores['health_score'],
            'delivery_score': scores['delivery_score'],
            'quality_score': scores['quality_score'],
            'financial_score': scores['financial_score'],
            'communication_score': scores['communication_score'],
            'status': status,
            'emoji': emoji,
            'late_deliveries': row['late_deliveries_last_6_months'],
            'defect_rate': row['defect_rate'],
            'gst_q1': row['gst_filed_q1'],
            'gst_q2': row['gst_filed_q2'],
            'gst_q3': row['gst_filed_q3'],
            'gst_q4': row['gst_filed_q4'],
            'advance_requests': row['advance_payment_requests']
        })
    
    # sort by health score ascending so red ones appear first
    results.sort(key=lambda x: x['health_score'])
    
    return results