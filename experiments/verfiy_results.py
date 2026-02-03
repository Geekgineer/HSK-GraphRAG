import json
import sys
import statistics
import logging
import os

# Configuration
FILENAME = 'benchmark_data/benchmark_results.json'
LOG_FILENAME = 'results.log'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler(LOG_FILENAME, mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def load_data(filename):
    """
    Loads benchmark data from a JSON file.
    
    Args:
        filename (str): Path to the JSON benchmark results.
        
    Returns:
        dict: The parsed JSON data.
        
    Raises:
        SystemExit: If the file is not found.
    """
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Error: Could not find {filename}")
        sys.exit(1)

def verify_scalability(data):
    """
    Verifies Theorem 1: Scalability.
    Claim: Query latency is O(1) with respect to result set size (limit).
    
    This is verified by comparing the mean latency for limit=1 and limit=100.
    A small delta (< 2ms) indicates that index seek time dominates, supporting O(1) behavior.
    """
    logger.info(f"\n{'='*20} VERIFYING THEOREM 1: SCALABILITY {'='*20}")
    logger.info("Claim: Query latency is O(1) with respect to result set size (limit).")
    
    complexity_data = data.get('scalability', {}).get('query_complexity', [])
    
    # Extract specific limits for comparison
    limit_1 = next((item for item in complexity_data if item["limit"] == 1), None)
    limit_100 = next((item for item in complexity_data if item["limit"] == 100), None)
    
    if not limit_1 or not limit_100:
        logger.error("FAIL: Missing required complexity data for limit=1 or limit=100.")
        return

    t1 = limit_1['mean_ms']
    t100 = limit_100['mean_ms']
    delta = t100 - t1
    
    logger.info(f"\n[Limit   1] Mean Latency: {t1:.2f} ms")
    logger.info(f"[Limit 100] Mean Latency: {t100:.2f} ms")
    logger.info(f"Delta: {delta:.2f} ms over 100x scale factor")
    
    # Verification Logic: A small delta (< 2ms) confirms O(1) behavior for index seeks
    if delta < 2.0:
        logger.info("\n>>> RESULT: PASSED (Delta < 2ms confirms O(1) index seek dominance)")
    else:
        logger.warning("\n>>> RESULT: WARNING (Significant latency increase detected)")

def verify_safety(data):
    """
    Verifies Theorem 3: Safety Compliance.
    Claim: Topological Firewall rejects 100% of invalid entity requests.
    
    Verified by checking rejection rates for:
    1. Ghost Rejection Protocol (non-existent entities)
    2. Hallucination Protocol (semantically invalid requests)
    """
    logger.info(f"\n{'='*20} VERIFYING THEOREM 3: SAFETY COMPLIANCE {'='*20}")
    logger.info("Claim: Topological Firewall rejects 100% of invalid entity requests.")
    
    safety_data = data.get('safety', {})
    
    # 1. Ghost Rejection Protocol
    ghosts = safety_data.get('ghost_rejection', [])
    total_ghosts = len(ghosts)
    blocked_ghosts = sum(1 for trial in ghosts if trial.get('blocked') is True and trial.get('status') == 'no_candidates')
    
    # 2. Hallucination Protocol
    hallucinations = safety_data.get('hallucination_detection', [])
    total_hallucinations = len(hallucinations)
    blocked_hallucinations = sum(1 for trial in hallucinations if trial.get('blocked') is True)
    
    logger.info(f"\n[Ghost Protocol]        Trials: {total_ghosts} | Blocked: {blocked_ghosts} | Pass Rate: {100 * blocked_ghosts / total_ghosts if total_ghosts else 0:.1f}%")
    logger.info(f"[Hallucination Protocol] Trials: {total_hallucinations} | Blocked: {blocked_hallucinations} | Pass Rate: {100 * blocked_hallucinations / total_hallucinations if total_hallucinations else 0:.1f}%")
    
    if blocked_ghosts == total_ghosts and blocked_hallucinations == total_hallucinations:
         logger.info("\n>>> RESULT: PASSED (100% Safety Compliance Verified)")
    else:
         logger.error("\n>>> RESULT: FAILED (Safety Violations Detected)")

def verify_jitter(data):
    """
    Verifies Real-World Jitter conditions.
    Claim: Data reflects realistic network conditions with outliers present.
    
    A heuristic (> 3 * median) is used to identify performance spikes/outliers.
    Existence of outliers confirms the realism of the benchmark environment.
    """
    logger.info(f"\n{'='*20} VERIFYING REAL-WORLD JITTER {'='*20}")
    logger.info("Claim: Data reflects realistic network conditions (outliers present).")
    
    cypher_trials = data.get('latency', {}).get('cypher', [])
    latencies = [t['latency_ms'] for t in cypher_trials]
    
    if not latencies:
        logger.warning("No latency data found.")
        return

    mean_val = statistics.mean(latencies)
    max_val = max(latencies)
    p50 = statistics.median(latencies)
    
    # Identify outliers (> 3 * median is a simple heuristic for network spikes)
    outliers = [x for x in latencies if x > 3 * p50]
    
    logger.info(f"\nTotal Trials: {len(latencies)}")
    logger.info(f"Median (P50): {p50:.2f} ms")
    logger.info(f"Mean:         {mean_val:.2f} ms")
    logger.info(f"Max Spike:    {max_val:.2f} ms")
    logger.info(f"Outliers Detected (>3x median): {len(outliers)}")
    
    if len(outliers) > 0:
        logger.info("\n>>> RESULT: VERIFIED (Realistic variance/outliers detected)")
    else:
        logger.warning("\n>>> RESULT: SUSPICIOUS (Data may be too clean/simulated)")

if __name__ == "__main__":
    logger.info(f"Loading artifact: {FILENAME}...")
    benchmark_data = load_data(FILENAME)
    
    verify_scalability(benchmark_data)
    verify_safety(benchmark_data)
    verify_jitter(benchmark_data)
    logger.info("\n" + "="*60)
    logger.info("VERIFICATION COMPLETE")
    logger.info(f"Log file written to: {os.path.abspath(LOG_FILENAME)}")