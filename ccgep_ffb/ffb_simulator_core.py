"""Core FFB simulation logic"""

import numpy as np
from ffb_parameters import FFBParameters


class FFBSimulator:
    """Simulates Force Feedback based on tire model"""
    
    # Predefined GTR2 slip curve from VBA
    TIRE_CURVE = [
        0.0, 0.0998647816612757, 0.198850437271588, 0.295873493665782,
        0.389644451141353, 0.478747424649196, 0.56178359192142, 0.637554401460092,
        0.705248331276834, 0.764547986620691, 0.815509139440791, 0.858530337038116,
        0.894236140716461, 0.923360033673105, 0.946656989027165, 0.96485363271285,
        0.978639812934221, 0.988654033276242, 0.99528134397826, 0.998528480165178,
        1.0, 0.999541463061979, 0.998237083578454, 0.996193708545235,
        0.99351818495813, 0.990317359812947, 0.986698080105495, 0.982767192831583,
        0.978631544987019, 0.974397983567612, 0.970173355569171, 0.966064507987504,
        0.962178287818419, 0.958558064482702, 0.954720318327627, 0.950615762783142,
        0.946336323007018, 0.94197392415703, 0.937620491390951, 0.933367949866554,
        0.929308224741612, 0.925533241173899, 0.922134924321188, 0.919185333516923,
        0.916416541442141, 0.913716717485577, 0.911085861647233, 0.908523973927107,
        0.906031054325201, 0.903607102841513, 0.901252119476043, 0.898966104228793,
        0.896749057099761, 0.894600978088949, 0.892521867196355, 0.890511724421979,
        0.888570549765823, 0.886698343227885, 0.884895104808166, 0.883160834506666,
        0.881495532323385, 0.87989909911099, 0.878344786015002, 0.876811700347376,
        0.87529984210811, 0.873809211297205, 0.872339807914662, 0.870891631960479,
        0.869464683434658, 0.868058962337197, 0.866674468668097, 0.865311202427359,
        0.863969163614981, 0.862648352230965, 0.861348768275309, 0.860070411748015,
        0.858813282649081, 0.857577380978508, 0.856362706736297, 0.855169259922446,
        0.853997040536956, 0.852846048579828, 0.85171628405106, 0.850607746950653,
        0.849520437278608, 0.848454355034923, 0.8474095002196, 0.846385872832637,
        0.845383472874035, 0.844402300343795, 0.843442355241915, 0.842503637568396,
        0.841586147323239, 0.840689884506442, 0.839814513818727, 0.8389502198343,
        0.838092459357331, 0.837241232387822, 0.836396538925772, 0.835558378971181,
        0.834726752524049, 0.833901659584376, 0.833083100152162, 0.832271074227408,
        0.831465581810112, 0.830666622900276, 0.829874197497898, 0.82908830560298,
        0.828308947215521, 0.82753612233552, 0.826769830962979, 0.826010073097897,
        0.825256848740274, 0.82451015789011, 0.823770000547405, 0.82303637671216,
        0.822309286384373, 0.821588729564045, 0.820874706251177, 0.820167216445768,
        0.819466260147817, 0.818771837357326, 0.818083948074294, 0.817402592298721,
        0.816727770030607, 0.816059481269952, 0.815397726016756, 0.814742504271019,
        0.814093816032741, 0.813451661301923, 0.812816040078563, 0.812186952362663,
        0.811564398154221, 0.810948377453239, 0.810338890259716, 0.809735936573652,
        0.809139516395047, 0.808549629723901, 0.807966276560214, 0.807389456903986,
        0.806819170755217, 0.806255418113908, 0.805698198980057, 0.805147513353666,
        0.804603361234733, 0.80406574262326, 0.803534657519245, 0.80301010592269,
        0.802492087833594, 0.801980603251957, 0.8
    ]
    
    def __init__(self):
        self.params = FFBParameters()
        self.curve_size = len(self.TIRE_CURVE) - 1  # 150
        
        # Calculate grip fraction curve
        self.grip_fract = self._calculate_grip_fraction()
        
        # Define load cases (inside/outside tire loads in N)
        self.load_cases = [
            (1000, 4000),  # Low load
            (2000, 6000),  # Medium load
            (3000, 8000)   # High load
        ]
        
        # Calculate mu (friction coefficient) for each load
        self.mu_values = []
        for loads in self.load_cases:
            inside_mu = 2.01 - loads[0] * 0.00012
            outside_mu = 2.01 - loads[1] * 0.00012
            self.mu_values.append((inside_mu, outside_mu))
        
        # Results storage
        self.ffb_results = []  # Will hold 3 arrays of FFB values
        self.slip_values = np.array([i * 0.6 for i in range(self.curve_size + 1)])
        
    def _calculate_grip_fraction(self):
        """Calculate mGripFract from tire curve"""
        grip_fract = np.ones(len(self.TIRE_CURVE))
        for i in range(2, len(self.TIRE_CURVE)):
            if i > 0 and self.TIRE_CURVE[1] != 0:
                grip_fract[i] = (self.TIRE_CURVE[i] / i) / self.TIRE_CURVE[1]
            else:
                grip_fract[i] = 1.0
        return grip_fract
    
    def ffb_4(self, tire_load0, tire_load1, grip_fract0, grip_fract1,
              lat_force0, lat_force1, long_force0=0, long_force1=0):
        """
        FFB_4 function from VBA including caster and KPI effects
        """
        # Pneumatic trail depends on tire load and slip
        pneu_trail0 = self.params.pneumatic_trail_nm * tire_load0 * (grip_fract0 ** self.params.grip_fract_power)
        pneu_trail1 = self.params.pneumatic_trail_nm * tire_load1 * (grip_fract1 ** self.params.grip_fract_power)
        
        # Total torque from lateral forces
        lat_torque0 = pneu_trail0 * lat_force0 + self.params.suspension_trail_m * lat_force0
        lat_torque1 = pneu_trail1 * lat_force1 + self.params.suspension_trail_m * lat_force1
        
        # Longitudinal forces add torque from scrub radius
        long_torque0 = long_force0 * self.params.suspension_scrub_m
        long_torque1 = long_force1 * -self.params.suspension_scrub_m
        
        # Sum torques
        torque0 = lat_torque0 + long_torque0
        torque1 = lat_torque1 + long_torque1
        
        # Convert torque to force at steering arm
        arm_length = self.params.steering_arm_length_m if self.params.steering_arm_length_m != 0 else 0.1
        force0 = torque0 / arm_length
        force1 = torque1 / arm_length
        
        # KPI and caster geometry effects
        kpi_moment0 = np.sin(self.params.kpi_angle_rad) * self.params.suspension_trail_m * tire_load0
        caster_moment0 = np.sin(self.params.caster_angle_rad) * self.params.suspension_scrub_m * tire_load0
        kpi_caster_force0 = (kpi_moment0 + caster_moment0) / arm_length
        
        kpi_moment1 = np.sin(self.params.kpi_angle_rad) * self.params.suspension_trail_m * tire_load1
        caster_moment1 = np.sin(self.params.caster_angle_rad) * self.params.suspension_scrub_m * tire_load1
        kpi_caster_force1 = -((kpi_moment1 + caster_moment1) / arm_length)
        
        # Total force
        total_force0 = force0 + kpi_caster_force0
        total_force1 = force1 + kpi_caster_force1
        
        # Scale and sum
        ffb = (total_force0 + total_force1) * self.params.gain
        
        # Gamma shaping
        x = ffb / 10000.0
        ffb = np.sign(x) * (np.abs(x) ** self.params.gamma) * 10000.0
        
        return ffb
    
    def calculate_all(self):
        """Calculate FFB for all load cases"""
        self.ffb_results = []
        
        for case_idx, ((inside_load, outside_load), (inside_mu, outside_mu)) in enumerate(zip(self.load_cases, self.mu_values)):
            ffb_case = np.zeros(self.curve_size + 1)
            
            for j in range(self.curve_size + 1):
                tire_curve = self.TIRE_CURVE[j]
                grip_fract = self.grip_fract[j]
                
                # Estimate lateral forces
                in_lat_force = inside_load * inside_mu * tire_curve * -1
                out_lat_force = outside_load * outside_mu * tire_curve * -1
                
                # Longitudinal forces set to 0 for this simulation
                in_long_force = 0
                out_long_force = 0
                
                ffb = self.ffb_4(inside_load, outside_load,
                                 grip_fract, grip_fract,
                                 in_lat_force, out_lat_force,
                                 in_long_force, out_long_force)
                
                ffb_case[j] = ffb
            
            self.ffb_results.append(ffb_case)
        
        # Auto gain if enabled
        if self.params.auto_gain:
            self._apply_auto_gain()
    
    def _apply_auto_gain(self):
        """Scale gain to hit 10000 maximum"""
        if not self.ffb_results:
            return
        
        # Find maximum FFB value across all cases
        max_ffb = 0.01
        for ffb_case in self.ffb_results:
            case_max = np.max(np.abs(ffb_case))
            if case_max > max_ffb:
                max_ffb = case_max
        
        # Calculate gain multiplier and apply
        gain_mult = 10000.0 / max_ffb
        self.params.gain *= gain_mult
        
        # Recalculate with new gain
        self.ffb_results = []
        for case_idx, ((inside_load, outside_load), (inside_mu, outside_mu)) in enumerate(zip(self.load_cases, self.mu_values)):
            ffb_case = np.zeros(self.curve_size + 1)
            
            for j in range(self.curve_size + 1):
                tire_curve = self.TIRE_CURVE[j]
                grip_fract = self.grip_fract[j]
                
                in_lat_force = inside_load * inside_mu * tire_curve * -1
                out_lat_force = outside_load * outside_mu * tire_curve * -1
                
                ffb = self.ffb_4(inside_load, outside_load,
                                 grip_fract, grip_fract,
                                 in_lat_force, out_lat_force,
                                 0, 0)
                
                ffb_case[j] = ffb
            
            self.ffb_results.append(ffb_case)
