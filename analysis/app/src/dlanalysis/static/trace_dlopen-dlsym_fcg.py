#!/usr/bin/env python3
import sys
from collections import defaultdict, deque

# Example usage: cat fcg.txt | grep -E "^DIRECT" | ./this_script.py

# Traces back the cfg, and provides output that is ready to render mermaid
# format. (For me It works while importing mermaid in excalidraw, I didnt test it with sth else.)

##############################################################################
# CONFIGURATION
##############################################################################

# We'll look for these functions as "targets" to trace backwards (ignoring module).
TARGET_CALLEE_NAMES = {"dlopen", "dlsym"}

def is_executable_module(module_str: str) -> bool:
    """Check if the module string indicates the executable, e.g. 'module-(executable)'."""
    return "(executable)" in module_str

def sanitize_label(label: str) -> str:
    """Replace or remove characters that might break Mermaid syntax."""
    return (label
            .replace(" ", "-")
            .replace("@@", "_")
            .replace("(", "")
            .replace(")", "")
            .replace(";", "-"))
def parse_hex_address(addr_str: str) -> int:
    """Safely parse a hex string like '1e8da0'. Return a large fallback if invalid."""
    try:
        return int(addr_str, 16)
    except ValueError:
        return 0xFFFFFFFF

##############################################################################
# 1. BUILD THE CALL GRAPH
#
#    - We unify each node by (module, function_name).
#    - We track the smallest address observed for each (module, func).
#    - We create a reverse mapping: (callee_mod, callee_func) -> set of (caller_mod, caller_func).
##############################################################################

callers_of = defaultdict(set)  # key: (mod, func), value: set of (mod, func)
min_addr_for_node = defaultdict(lambda: 0xFFFFFFFFFFFFFFFF)
modules_for_node = defaultdict(set)  # (mod, func) -> {module_str}, typically just one but we store a set.

def update_min_address(node_key, addr_str):
    val = parse_hex_address(addr_str)
    if val < min_addr_for_node[node_key]:
        min_addr_for_node[node_key] = val

for line in sys.stdin:
    line = line.strip()
    if not line.startswith("DIRECT "):
        continue

    parts = line.split(None, 7)
    if len(parts) < 7:
        continue

    # Fields:
    #   0: "DIRECT"
    #   1: module-<caller_module>
    #   2: caller_addr
    #   3: caller_func
    #   4: callee_addr
    #   5: callee_func
    #   6: module-<callee_module>
    caller_module = parts[1]
    caller_addr   = parts[2]
    caller_func   = parts[3]
    callee_addr   = parts[4]
    callee_func   = parts[5]
    callee_module = parts[6]

    caller_node = (caller_module, caller_func)
    callee_node = (callee_module, callee_func)

    # Update smallest addresses
    update_min_address(caller_node, caller_addr)
    update_min_address(callee_node, callee_addr)

    # Track modules
    modules_for_node[caller_node].add(caller_module)
    modules_for_node[callee_node].add(callee_module)

    # Reverse edge: callee -> caller
    callers_of[callee_node].add(caller_node)

# Convert defaultdict to dict so we don't mutate it during BFS
callers_of = dict(callers_of)

##############################################################################
# 2. BACKWARD TRAVERSAL (BFS)
#
#    For each node whose (function_name minus @@...) is in TARGET_CALLEE_NAMES,
#    trace upward until we reach a function in the executable module.
##############################################################################

found_edges = set()  # store edges as ((caller_mod, caller_func), (callee_mod, callee_func))

def trace_backwards_from(start_node):
    queue = deque([start_node])
    visited = set([start_node])

    while queue:
        current = queue.popleft()

        # If current node is in the executable, stop going upward.
        node_modules = modules_for_node[current]
        if any(is_executable_module(m) for m in node_modules):
            continue

        # For each direct caller
        for parent_node in callers_of.get(current, set()):
            found_edges.add((parent_node, current))
            if parent_node not in visited:
                visited.add(parent_node)
                queue.append(parent_node)

# Identify any node whose base function name is in our target set.
all_callee_nodes = list(callers_of.keys())
for node_key in all_callee_nodes:
    mod, func = node_key
    base_name = func.split("@@")[0]
    if base_name in TARGET_CALLEE_NAMES:
        trace_backwards_from(node_key)

##############################################################################
# 3. BUILD A SET OF ALL NODES USED IN found_edges
##############################################################################

used_nodes = set()
for (caller_node, callee_node) in found_edges:
    used_nodes.add(caller_node)
    used_nodes.add(callee_node)

##############################################################################
# 4. GROUP NODES BY MODULE, SO WE CAN PRINT SUBGRAPHS
##############################################################################

nodes_by_module = defaultdict(list)
for (module_str, func_name) in used_nodes:
    nodes_by_module[module_str].append(func_name)

# Sort modules for stable output
sorted_modules = sorted(nodes_by_module.keys())

##############################################################################
# 5. OUTPUT MERMAID CODE
#
#    We'll do:
#       graph LR
#       subgraph <module_str>
#           node labels...
#       end
#       edges...
##############################################################################

print("```mermaid")
print("graph LR;")

# 5a. Print each module as a subgraph, define all relevant nodes
for module_str in sorted_modules:
    # Start subgraph
    safe_module_label = sanitize_label(module_str)
    print(f'    subgraph {safe_module_label}')
    # Indent further for nodes
    for func_name in nodes_by_module[module_str]:
        # Build a label: 0x{min_addr}-{func_name}-{module_str}
        node_key = (module_str, func_name)
        addr_val = min_addr_for_node[node_key]
        node_label_full = f"0x{addr_val:x}-{func_name}-{module_str}"
        node_label_sanitized = sanitize_label(node_label_full)
        # In Mermaid, we can define a node by referencing it. We'll just do "id[label]" or something simple.
        # We'll use the sanitized label as the node ID to keep it unique.
        print(f'        "{node_label_sanitized}"["{node_label_sanitized}"]')
    # End subgraph
    print(f'    end')

# 5b. Now print edges
for (caller_node, callee_node) in found_edges:
    caller_mod, caller_func = caller_node
    callee_mod, callee_func = callee_node

    caller_addr_val = min_addr_for_node[caller_node]
    callee_addr_val = min_addr_for_node[callee_node]

    caller_label = f"0x{caller_addr_val:x}-{caller_func}-{caller_mod}"
    callee_label = f"0x{callee_addr_val:x}-{callee_func}-{callee_mod}"

    caller_label_s = sanitize_label(caller_label)
    callee_label_s = sanitize_label(callee_label)

    # Create an arrow between these two node IDs
    print(f'    "{caller_label_s}" --> "{callee_label_s}";')

print("```")