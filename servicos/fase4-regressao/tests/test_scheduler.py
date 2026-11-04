"""Ciclo de vida por processo, sem banco real ou produtor remanescente."""

import threading
import unittest
from unittest.mock import patch

from src.frontend import scheduler


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        scheduler.encerrar_scheduler()
        self.interval = patch.object(scheduler, "INTERVALO", 60)
        self.interval.start()

    def tearDown(self):
        scheduler.encerrar_scheduler()
        self.interval.stop()

    def test_multiple_sessions_share_only_one_producer(self):
        first, second = {}, {}
        scheduler.iniciar_scheduler(first)
        scheduler.iniciar_scheduler(first)
        scheduler.iniciar_scheduler(second)
        self.assertIs(first["scheduler"], second["scheduler"])
        self.assertEqual(len(first["scheduler"].get_jobs()), 1)
        self.assertTrue(first["scheduler"].running)
        self.assertEqual(first["iniciado_em"], second["iniciado_em"])

    def test_concurrent_sessions_share_only_one_producer(self):
        holders = [{} for _ in range(8)]
        threads = [threading.Thread(target=scheduler.iniciar_scheduler, args=(holder,)) for holder in holders]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len({id(holder["scheduler"]) for holder in holders}), 1)

    def test_stop_and_restart_are_idempotent(self):
        holder = {}
        scheduler.iniciar_scheduler(holder)
        old = holder["scheduler"]
        scheduler.encerrar_scheduler(holder)
        scheduler.encerrar_scheduler(holder)
        self.assertFalse(old.running)
        self.assertNotIn("scheduler", holder)
        scheduler.iniciar_scheduler(holder)
        self.assertTrue(holder["scheduler"].running)
        self.assertIsNot(holder["scheduler"], old)

    def test_direct_shutdown_object_does_not_prevent_restart(self):
        holder = {}
        scheduler.iniciar_scheduler(holder)
        old = holder["scheduler"]
        old.shutdown(wait=True)
        scheduler.iniciar_scheduler(holder)
        self.assertTrue(holder["scheduler"].running)
        self.assertIsNot(holder["scheduler"], old)

    def test_job_uses_simulation_backend_once(self):
        holder = {}
        with patch("src.db.database.inserir_leitura_simulada") as insert:
            scheduler.iniciar_scheduler(holder)
            holder["scheduler"].get_job("simulacao_iot").func()
        insert.assert_called_once()
        self.assertTrue(0 <= insert.call_args.kwargs["umidade"] <= 100)

    def test_controlled_cleanup_leaves_no_scheduler_thread(self):
        holder = {}
        scheduler.iniciar_scheduler(holder)
        scheduler.encerrar_scheduler(holder)
        self.assertFalse(any(thread.name == "APScheduler" for thread in threading.enumerate()))

    def test_designated_consumers_can_disable_producer(self):
        holder = {}
        with patch.dict("os.environ", {"FARMTECH_SIMULACAO": "0"}):
            scheduler.iniciar_scheduler(holder)
        self.assertNotIn("scheduler", holder)

    def test_invalid_interval_does_not_start_scheduler(self):
        with patch.object(scheduler, "INTERVALO", 0):
            with self.assertRaises(ValueError):
                scheduler.iniciar_scheduler({})
        self.assertIsNone(scheduler._SCHEDULER)


if __name__ == "__main__":
    unittest.main()
