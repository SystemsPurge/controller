import dpsimpy
import os

from villas.controller.components.simulator import Simulator


class DPsimSimulator(Simulator):

    def __init__(self, **args):
        self.sim = None

        super().__init__(**args)

    @property
    def headers(self):
        headers = super().headers

        headers['type'] = 'dpsim'
        headers['version'] = '0.1.0'

        return headers

    def load_cim(self, fp):
        if fp is not None:
            reader = dpsimpy.CIMReader(fp)
            files = list(map(lambda x: f'{fp}/{x}',os.listdir(fp)))
            self.logger.info(files)
            freq = self.params.get("system-freq",50)
            duration = self.params.get("duration",10)
            timestep = self.params.get("timestep",1)
            domain_str = self.params.get("solver-domain","SP")
            solver_str = self.params.get("solver-type","MNA")
            
            if domain_str == "SP":
                domain = dpsimpy.Domain.SP
            elif domain_str == "DP":
                domain = dpsimpy.Domain.DP
            else :
                domain = dpsimpy.Domain.EMT

            if solver_str == "MNA":
                solver = dpsimpy.Solver.MNA
            else:
                solver = dpsimpy.Solver.NRP
            
            system = reader.loadCIM(freq, files, domain, dpsimpy.PhaseType.Single, dpsimpy.GeneratorType.PVNode) #self.params system-freq
            self.sim = dpsimpy.Simulation(fp)
            self.sim.set_system(system)
            self.sim.set_domain(domain) #self.params solver-domain
            self.sim.set_solver(solver) #self.params solver-type
            self.sim.set_time_step(timestep) #self.params timestep
            self.sim.set_final_time(duration) #self.params duration
            logger = dpsimpy.Logger(fp)
            for node in system.nodes:
                logger.log_attribute(node.name()+'.V', 'v', node)
            self.sim.add_logger(logger)
            self.logger.info(self.sim)
            os.unlink(fp)

    def start(self, payload):
        super().start(payload)
        fp = self.download_model()
        if fp:
            self.load_cim(fp)

        if self.change_state('starting'):
            self.logger.info('Starting simulation...')

            self.logger.info(self.sim)
            if self.sim.start() is None:
                self.change_state('running')
            else:
                self.change_to_error('failed to start simulation')
                self.logger.warn('Attempt to start simulator failed.'
                                 'State is %s', self._state)
        else:
            self.logger.warn('Attempted to start non-stopped simulator.'
                             'State is %s', self._state)

    def stop(self, payload):
        if self._state == 'running':
            self.logger.info('Stopping simulation...')

            if self.sim and self.sim.stop() is None:
                self.change_state('stopped')
                self.logger.warn('State changed to ' + self._state)
            else:
                self.change_state('unknown')
                self.logger.warn('Attempt to stop simulator failed.'
                                 'State is %s', self._state)
        else:
            self.logger.warn('Attempted to stop non-stopped simulator.'
                             'State is %s', self._state)

    def pause(self, payload):
        if self._state == 'running':
            self.logger.info('Pausing simulation...')

            self._state = 'pausing'

            try:
                if self.sim and self.sim.pause() is None:
                    self.change_state('paused')
                    self.logger.warn('State changed to ' + self._state)
                else:
                    self.logger.warn('Attempted to pause simulator failed.')
                    self.change_state('unknown')

            except SystemError as e:
                self.logger.warn('Attempted to pause simulator failed.'
                                 'Error is ' + str(e))
                self.change_state('unknown')

        else:
            self.logger.warn('Attempted to pause non-running simulator.'
                             'State is ' + self._state)

    def resume(self, payload):
        if self._state == 'paused':
            self.logger.info('Resuming simulation...')

            self._state = 'resuming'

            try:
                if self.sim and self.sim.start() is None:
                    self.change_state('running')
                    self.logger.warn('State changed to %s', self._state)
                else:
                    self.logger.warn('Attempted to resume simulator failed.')
                    self.change_state('unknown')

            except SystemError as e:
                self.logger.warn('Attempted to pause simulator failed. '
                                 'Error is %s', str(e))
                self.change_state('unknown')

        else:
            self.logger.warn('Attempted to resume non-paused simulator.'
                             'State is %s', self._state)
