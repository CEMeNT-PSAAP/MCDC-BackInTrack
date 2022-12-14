import numpy as np
import type_, kernel, adapter

from numba import objmode

from constant import *

simulation = None

# =============================================================================
# History-based
# =============================================================================

def HISTORY_simulation(mcdc, hostco):
    # =========================================================================
    # Simulation loop
    # =========================================================================

    for i_history in range(mcdc['N_history']):
        # =====================================================================
        # Initialize history
        # =====================================================================

        # Create particle
        P = kernel.create(type_.particle)

        # Set RNG seed
        P['seed'] = mcdc['seed']
        kernel.rng_skip_ahead(i_history*mcdc['history_stride'], P, mcdc)

        # Initialize particle
        kernel.source(P, mcdc)
        
        # "Push" to the bank
        mcdc['bank']['content'][0] = kernel.record_particle(P)
        mcdc['bank']['size']       = 1

        # Reset main seed
        mcdc['seed'] = P['seed']

        # =====================================================================
        # History loop
        # =====================================================================

        while mcdc['bank']['size'] > 0:
            # =================================================================
            # Initialize particle
            # =================================================================

            # "Pop" particle from bank
            mcdc['bank']['size'] -= 1
            idx = mcdc['bank']['size']
            P = kernel.read_particle(mcdc['bank']['content'][idx])

            # Set particle seed
            P['seed'] = mcdc['seed']

            # =================================================================
            # Particle loop
            # =================================================================

            # Particle loop
            while P['alive']:
                # Move to event
                kernel.move(P, mcdc)

                # Event
                event = P['event']

                # Collision
                if event == EVENT_SCATTERING:
                    kernel.scattering(P, mcdc)
                elif event == EVENT_FISSION:
                    kernel.fission(P, mcdc)
                elif event == EVENT_LEAKAGE:
                    kernel.leakage(P, mcdc)
                elif event == EVENT_BRANCHLESS_COLLISION:
                    kernel.branchless_collision(P, mcdc)

            # Update main seed
            mcdc['seed'] = P['seed']

# =============================================================================
# Event-based
# =============================================================================

def EVENT_simulation(mcdc, hostco):
    # =========================================================================
    # Initialize simulation
    # =========================================================================

    kernel.initialize_stack(mcdc, hostco)

    # =========================================================================
    # Simulation loop
    # =========================================================================

    it = 0
    while np.max(hostco['stack_size'][1:]) > 0:
        it += 1
        # =====================================================================
        # Initialize event
        # =====================================================================
    
        # Determine next event executed based on the longest stack
        stack = np.argmax(hostco['stack_size'][1:]) + 1 # Offset for EVENT_NONE
        event = hostco['event_idx'][stack]

        # =================================================================
        # Event loop
        # =================================================================

        if event == EVENT_SOURCE:
            kernel.source(mcdc, hostco)
        elif event == EVENT_MOVE:
            kernel.move(mcdc, hostco)
        elif event == EVENT_SCATTERING:
            kernel.scattering(mcdc, hostco)
        elif event == EVENT_FISSION:
            kernel.fission(mcdc, hostco)
        elif event == EVENT_LEAKAGE:
            kernel.leakage(mcdc, hostco)
        elif event == EVENT_BRANCHLESS_COLLISION:
            kernel.branchless_collision(mcdc, hostco)

        '''
        print(hostco['stack_size'])
        print(mcdc['stack_']['size'])
        for i in range(hostco['stack_size'].shape[0]):
            size = mcdc['stack_'][i]['size']
            if size > 0:
                print(i, size, mcdc['stack_'][i]['content'][:size])
        print(mcdc['bank'])
        print('\n\n')
        '''


# =============================================================================
# Factory
# =============================================================================

def make_loops(alg, target):
    global simulation
    if alg == 'history':
        simulation = adapter.loop(HISTORY_simulation, target)
    else:
        simulation = adapter.loop(EVENT_simulation, target)
